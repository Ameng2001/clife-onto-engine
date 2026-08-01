#!/usr/bin/env python3
"""重建自托管中文字体子集。

课件与手册用到的汉字是有限集（当前约 1.7k 字），全量 Noto Sans/Serif SC
可变字体是 17MB / 25MB，无法入库；本脚本扫描教材实际用到的字符，
用 pyftsubset 生成 woff2 子集，保留 wght 可变轴（课件用到 font-weight:750，
静态字重会被舍入）。

**教材内容增删汉字后需要重跑本脚本**，否则新字会回退到系统字体
（只影响那几个字的字形，不会报错、不会破版）。

用法：
    pip install 'fonttools[woff]' brotli
    python3 rebuild.py

依赖网络（从 google/fonts 取可变字体源）。
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # FDE课程/

SOURCES = {
    "NotoSansSC": "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
    "NotoSerifSC": "https://github.com/google/fonts/raw/main/ofl/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",
}

# 除实际用字外，额外兜底纳入的区段：中文标点、全角符号、常用箭头与项目符号。
# 这些字符量小但极易在后续编辑中新增，纳入可减少重跑频率。
EXTRA_RANGES = [
    (0x3000, 0x303F),   # CJK 标点
    (0xFF00, 0xFF60),   # 全角 ASCII
    (0xFFE0, 0xFFE5),   # 全角货币符号
    (0x2010, 0x2027),   # 破折号 / 引号 / 省略号
    (0x2030, 0x205E),   # ‰ † ‡ 等
    (0x2190, 0x21FF),   # 箭头
    (0x2460, 0x24FF),   # ① ② ③ 带圈数字
    (0x25A0, 0x25FF),   # ■ ● ▲ 几何符号
    (0x00A0, 0x00FF),   # 拉丁补充（° × ÷ 等）
]


def collect_chars() -> set:
    """扫描教材全部 md / html，收集实际出现的字符。"""
    chars = set()
    n_files = 0
    for root, dirs, files in os.walk(COURSE_ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "fonts")]
        for fn in files:
            if not fn.endswith((".md", ".html")):
                continue
            path = os.path.join(root, fn)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            # html：剥掉脚本、样式与标签，只留可见文本
            if fn.endswith(".html"):
                text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S)
                text = re.sub(r"<[^>]+>", " ", text)
            chars |= set(text)
            n_files += 1
    for lo, hi in EXTRA_RANGES:
        chars |= {chr(c) for c in range(lo, hi + 1)}
    # 只保留 BMP 内可编码字符，去掉控制符
    chars = {c for c in chars if c.isprintable() and ord(c) < 0x10000}
    print(f"  扫描 {n_files} 个文件，字符集 {len(chars)} 个"
          f"（其中汉字 {len([c for c in chars if '一' <= c <= '鿿'])} 个）")
    return chars


def build(name: str, url: str, charset: set, outdir: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as tmp:
        src = tmp.name
    try:
        print(f"  [{name}] 下载源文件…", end="", flush=True)
        urllib.request.urlretrieve(url, src)
        print(f" {os.path.getsize(src) / 1048576:.1f} MB")

        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as tf:
            tf.write("".join(sorted(charset)))
            txt = tf.name

        out = os.path.join(outdir, f"{name}-subset.woff2")
        subprocess.run(
            [sys.executable, "-m", "fontTools.subset", src,
             f"--text-file={txt}",
             "--flavor=woff2",
             f"--output-file={out}",
             "--layout-features=*",
             "--name-IDs=*",
             "--notdef-outline"],
            check=True, capture_output=True,
        )
        os.unlink(txt)

        from fontTools.ttLib import TTFont
        f = TTFont(out)
        axes = [(a.axisTag, a.minValue, a.maxValue) for a in f["fvar"].axes] if "fvar" in f else None
        print(f"  [{name}] → {os.path.basename(out)}  "
              f"{os.path.getsize(out) / 1024:.0f} KB  字形 {f['maxp'].numGlyphs}  轴 {axes}")
        if not axes:
            print(f"  ⚠️ [{name}] 可变轴丢失，font-weight:750 之类的非标准字重会失真")
    finally:
        os.path.exists(src) and os.unlink(src)


def main() -> None:
    print("重建自托管中文字体子集")
    charset = collect_chars()
    for name, url in SOURCES.items():
        build(name, url, charset, HERE)
    print("\n完成。若字形有缺失，检查是否新增了汉字后忘记重跑本脚本。")


if __name__ == "__main__":
    main()
