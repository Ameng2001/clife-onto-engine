"""把运行时对象图导为自有 Explorer（离线单文件 HTML）。

运行：python scripts/export_explorer.py   → build/explorer/<ontology>.html

自有展示：不依赖 UModel 就能浏览治理对象图。cytoscape 从 vendored 内联 → 完全离线自包含。
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.explorer import render
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401

from repl import seed  # 复用 REPL demo 数据 seed（grass/chili）

# vendored cytoscape（来自 third-party/okf-visualizer；调用层注入，kernel 模块不触 third-party）
_CYTO = (ROOT / "third-party" / "okf-visualizer" / "reference_agent" / "viewer"
         / "static" / "vendor" / "cytoscape.min.js").read_text(encoding="utf-8")


def main() -> None:
    out_dir = ROOT / "build" / "explorer"
    out_dir.mkdir(parents=True, exist_ok=True)
    for ns in ("grass", "chili"):
        store = InMemoryStore()
        seed(store, ns)
        html = render(spi.registry, store, ns, cytoscape_js=_CYTO)
        path = out_dir / f"{ns}.html"
        path.write_text(html, encoding="utf-8")
        n_nodes = html.count('"otype"')
        offline = "✓ 完全离线" if 'src="https' not in html else "✗ 仍有外链"
        print(f"== {ns}: {n_nodes} 节点 · {offline} → {path.relative_to(ROOT)} ==")


if __name__ == "__main__":
    main()
