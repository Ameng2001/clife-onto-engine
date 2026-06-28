"""把本体导出为 OKF v0.1 知识包，并自检合规性。

运行：  python scripts/export_okf.py   → 输出到 build/okf/<ontology>/
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import yaml

from clife_onto_engine.okf import export_bundle
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401

ROOT = pathlib.Path(__file__).resolve().parent.parent

# vendored OKF 参考可视化器（Google，Apache-2.0；见 third-party/okf-visualizer/PROVENANCE.md）
sys.path.insert(0, str(ROOT / "third-party" / "okf-visualizer"))
from reference_agent.viewer import generate_visualization  # noqa: E402
from reference_agent.viewer import generator as _okf_gen  # noqa: E402

# 运行时给本体五类概念上色（不改 vendored 文件；to_node 调用时读这两个模块全局）
_okf_gen._TYPE_PALETTE = {
    "ontology-object": "#3b82f6",    # 对象 蓝
    "ontology-link": "#94a3b8",      # 关系 灰
    "ontology-function": "#a855f7",  # 函数 紫
    "ontology-rule": "#ef4444",      # 规则 红（受治理，最显眼）
    "ontology-action": "#22c55e",    # 动作 绿
}
_okf_gen._DEFAULT_NODE_COLOR = "#cbd5e1"


_VENDOR = ROOT / "third-party" / "okf-visualizer" / "reference_agent" / "viewer" / "static" / "vendor"


# 图例显示顺序与中文标签（颜色取自 _okf_gen._TYPE_PALETTE，单一来源不漂移）
_LEGEND_ORDER = [
    ("ontology-object", "对象 Object"),
    ("ontology-rule", "规则 Rule"),
    ("ontology-action", "动作 Action"),
    ("ontology-function", "函数 Function"),
    ("ontology-link", "关系 Link"),
]


def _inject_legend(html: str) -> str:
    rows = "".join(
        f'<div class="okf-lg-row"><span class="okf-lg-dot" '
        f'style="background:{_okf_gen._TYPE_PALETTE[t]}"></span>{label}</div>'
        for t, label in _LEGEND_ORDER
    )
    block = (
        '<div id="okf-legend"><div class="okf-lg-title">本体类型</div>' + rows + "</div>"
        "<style>"
        "#okf-legend{position:fixed;left:16px;bottom:16px;z-index:9999;"
        "background:rgba(255,255,255,.95);border:1px solid #e2e8f0;border-radius:8px;"
        "padding:10px 12px;font:12px/1.7 -apple-system,system-ui,sans-serif;"
        "box-shadow:0 2px 10px rgba(0,0,0,.1);color:#334155}"
        "#okf-legend .okf-lg-title{font-weight:600;margin-bottom:4px;color:#0f172a}"
        ".okf-lg-row{display:flex;align-items:center;gap:7px}"
        ".okf-lg-dot{width:11px;height:11px;border-radius:50%;display:inline-block;flex:0 0 auto}"
        "</style>"
    )
    return html.replace("</body>", block + "\n</body>")


def _inline_offline(html: str) -> str:
    """把 viz.html 里的 CDN <script src> 替换为 vendored 库内联 → 完全离线自包含。"""
    def repl(m: re.Match) -> str:
        name = m.group(1).rsplit("/", 1)[-1]
        lib = _VENDOR / name
        if lib.exists():
            return "<script>\n" + lib.read_text(encoding="utf-8") + "\n</script>"
        return m.group(0)  # 未知库保留（容错）
    return re.sub(r'<script src="(https://[^"]+)"></script>', repl, html)


def _conformance(bundle: pathlib.Path) -> tuple[int, list[str]]:
    """OKF v0.1：非保留 .md 必须有可解析 frontmatter 且含非空 type。"""
    bad, n = [], 0
    for md in bundle.rglob("*.md"):
        if md.name in ("index.md", "log.md"):
            continue
        n += 1
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            bad.append(f"{md}: 无 frontmatter"); continue
        fm = yaml.safe_load(text.split("---", 2)[1])
        if not (isinstance(fm, dict) and fm.get("type")):
            bad.append(f"{md}: 缺非空 type")
    return n, bad


def main() -> None:
    for ns in ("grass", "chili"):
        out = ROOT / "build" / "okf" / ns
        bundle = export_bundle(spi.registry, ns, str(out), timestamp="2026-06-28")
        n, bad = _conformance(bundle)
        files = sorted(p.relative_to(bundle).as_posix() for p in bundle.rglob("*.md"))
        # vendored 可视化器：bundle → 交互式知识图谱 HTML（OKF 互操作的活证据）
        viz_path = bundle / "viz.html"
        viz = generate_visualization(bundle, viz_path, bundle_name=ns)
        # 内联 vendored JS 库 → 完全离线自包含（数据与库都不出本地）+ 注入类型图例
        html = _inline_offline(viz_path.read_text(encoding="utf-8"))
        html = _inject_legend(html)
        viz_path.write_text(html, encoding="utf-8")
        offline = "✓ 完全离线" if 'src="https' not in html else "✗ 仍有外链"
        print(f"== {ns}: {len(files)} 概念，OKF 合规 {'✓' if not bad else '✗ ' + str(bad)}"
              f" | 可视化 {viz['concepts']} 节点 {viz['edges']} 边，{offline} → {viz_path.relative_to(ROOT)} ==")
        for f in files:
            print(f"   {f}")

    print("\n== 样例：grass 的治理规则 乡土合规（带出处+引用）==")
    print((ROOT / "build/okf/grass/rules/乡土合规.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
