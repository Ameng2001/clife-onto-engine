#!/usr/bin/env python3
"""重建自托管字体子集（中文 + 拉丁 / 等宽）。

课件与手册用到的字符是有限集，而字体源文件动辄十几 MB（中文尤甚），
无法整份入库。本脚本扫描教材实际用到的字符，用 pyftsubset 生成 woff2 子集。

设计要点：
- **同一份字符集喂给所有字体**。拉丁字体里没有的汉字会被自动忽略，
  因此不需要为中西文维护两套字符集。
- **优先用可变字体**（保留 wght 轴），单文件覆盖全字重 —— 课件用到
  font-weight:750，静态字重会被舍入。IBM Plex Mono 与 Archivo Black
  在 google/fonts 只有静态版，按字重分别产出。

**教材内容增删字符后需要重跑本脚本**，否则新字符回退到系统字体
（只影响那几个字的字形，不会报错、不会破版）。

用法：
    pip install 'fonttools[woff]' brotli
    python3 rebuild.py            # 全部重建
    python3 rebuild.py --cjk      # 只重建中文（改教材后通常只需这个）

依赖网络（从 google/fonts 取源文件）。
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # FDE课程/
RAW = "https://github.com/google/fonts/raw/main/ofl"

# (输出名, 源 URL, 是否中文)
FONTS = [
    # ── 中文（体积大头，占子集总量九成以上）
    ("NotoSansSC",           f"{RAW}/notosanssc/NotoSansSC%5Bwght%5D.ttf",                  True),
    ("NotoSerifSC",          f"{RAW}/notoserifsc/NotoSerifSC%5Bwght%5D.ttf",                True),
    # ── 拉丁 / 等宽（可变）
    ("Inter",                f"{RAW}/inter/Inter%5Bopsz,wght%5D.ttf",                       False),
    ("JetBrainsMono",        f"{RAW}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",            False),
    ("PlayfairDisplay",      f"{RAW}/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",        False),
    ("PlayfairDisplay-Italic", f"{RAW}/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf", False),
    ("SpaceGrotesk",         f"{RAW}/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf",              False),
    # ── 拉丁 / 等宽（静态，google/fonts 无可变版）
    ("IBMPlexMono-300",      f"{RAW}/ibmplexmono/IBMPlexMono-Light.ttf",                    False),
    ("IBMPlexMono-400",      f"{RAW}/ibmplexmono/IBMPlexMono-Regular.ttf",                  False),
    ("IBMPlexMono-500",      f"{RAW}/ibmplexmono/IBMPlexMono-Medium.ttf",                   False),
    ("IBMPlexMono-700",      f"{RAW}/ibmplexmono/IBMPlexMono-Bold.ttf",                     False),
    ("ArchivoBlack",         f"{RAW}/archivoblack/ArchivoBlack-Regular.ttf",                False),
]

# 除实际用字外额外兜底的区段：这些字符量小但极易在后续编辑中新增，
# 纳入可减少重跑频率。
EXTRA_RANGES = [
    (0x0020, 0x007E),   # ASCII 可打印
    (0x00A0, 0x00FF),   # 拉丁补充（° × ÷ 等）
    (0x2010, 0x2027),   # 破折号 / 引号 / 省略号
    (0x2030, 0x205E),   # ‰ † ‡ 等
    (0x20A0, 0x20BF),   # 货币符号
    (0x2190, 0x21FF),   # 箭头
    (0x2200, 0x22FF),   # 数学运算符
    (0x2460, 0x24FF),   # ① ② ③ 带圈数字
    (0x25A0, 0x25FF),   # ■ ● ▲ 几何符号
    (0x3000, 0x303F),   # CJK 标点
    (0xFF00, 0xFF60),   # 全角 ASCII
    (0xFFE0, 0xFFE5),   # 全角货币符号
]


def collect_chars() -> set:
    """扫描教材全部 md / html，收集实际出现的字符。"""
    chars, n_files = set(), 0
    for root, dirs, files in os.walk(COURSE_ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "fonts")]
        for fn in files:
            if not fn.endswith((".md", ".html")):
                continue
            try:
                text = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if fn.endswith(".html"):
                text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S)
                text = re.sub(r"<[^>]+>", " ", text)
            chars |= set(text)
            n_files += 1
    for lo, hi in EXTRA_RANGES:
        chars |= {chr(c) for c in range(lo, hi + 1)}
    chars = {c for c in chars if c.isprintable() and ord(c) < 0x10000}
    cjk = len([c for c in chars if "一" <= c <= "鿿"])
    print(f"  扫描 {n_files} 个文件 → 字符集 {len(chars)}（汉字 {cjk}）")
    return chars


def build(name: str, url: str, charset: set) -> int:
    with tempfile.NamedTemporaryFile(suffix=".ttf", delete=False) as t:
        src = t.name
    try:
        urllib.request.urlretrieve(url, src)
        raw_kb = os.path.getsize(src) / 1024
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as tf:
            tf.write("".join(sorted(charset)))
            txt = tf.name
        out = os.path.join(HERE, f"{name}-subset.woff2")
        subprocess.run(
            [sys.executable, "-m", "fontTools.subset", src,
             f"--text-file={txt}", "--flavor=woff2", f"--output-file={out}",
             "--layout-features=*", "--name-IDs=*", "--notdef-outline"],
            check=True, capture_output=True,
        )
        os.unlink(txt)
        from fontTools.ttLib import TTFont
        f = TTFont(out)
        axes = ",".join(f"{a.axisTag} {a.minValue:g}-{a.maxValue:g}" for a in f["fvar"].axes) if "fvar" in f else "静态"
        kb = os.path.getsize(out) / 1024
        print(f"  {name:<24} {raw_kb/1024:>5.1f}MB → {kb:>6.0f}KB   字形 {f['maxp'].numGlyphs:<5} {axes}")
        return os.path.getsize(out)
    finally:
        os.path.exists(src) and os.unlink(src)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cjk", action="store_true", help="只重建中文字体")
    args = ap.parse_args()

    print("重建自托管字体子集")
    charset = collect_chars()
    targets = [f for f in FONTS if f[2]] if args.cjk else FONTS
    total = sum(build(name, url, charset) for name, url, _ in targets)
    print(f"\n  合计 {total/1048576:.2f} MB / {len(targets)} 个文件")
    print("  若字形有缺失，检查是否新增了字符后忘记重跑本脚本。")


if __name__ == "__main__":
    main()
