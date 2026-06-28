"""冒烟：GraphStore SPI（对象/关系/search_around + overlay 写即可见）与映射注册表。

运行：  python scripts/smoke_graphstore.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # 仓库根入 path

from clife_onto_engine.query import InMemoryGraphStore, QueryView, StagedLink
from clife_onto_engine.sdk import Materialization, spi

import plugins.grass  # noqa: F401 — import 即注册 schema + 映射


def main() -> None:
    store = InMemoryGraphStore()
    # 基底：两节点 + 一条已持久化的边
    store.put_object("Degradation", "deg1", {"level": "重度", "type": "盐渍化"})
    store.put_object("RestorationMethod", "m_喷播", {"name": "喷播"})
    store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_喷播", {"applicability": 0.9}))

    print("== Search Around（基底）==")
    for h in store.search_around("Degradation", "deg1", "treated_by"):
        print(f"  deg1 -treated_by-> {h.node_type}:{h.node_key} {h.node} edge={h.edge_props}")
    print("  反向 in：", [(h.node_type, h.node_key) for h in
                          store.search_around("RestorationMethod", "m_喷播", "treated_by", direction="in")])

    print("== overlay 写即可见（暂存边未落库即可被 search_around 看到）==")
    overlay: list = []
    view = QueryView(store, overlay)
    store.put_object("RestorationMethod", "m_补播", {"name": "补播"})
    overlay.append(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_补播", {"applicability": 0.7}))
    seen = [(h.node_key, h.edge_props) for h in view.search_around("Degradation", "deg1", "treated_by")]
    print(f"  base+overlay 邻居: {seen}")
    print(f"  base 单独（不含暂存）: {[h.node_key for h in store.search_around('Degradation', 'deg1', 'treated_by')]}")

    print("== 映射注册表（grass 槽位 2）==")
    site = spi.mappings.get_object("grass", "Site")
    print(f"  Site: 物化={site.materialization.value} 主源={site.primary.store}.{site.primary.table} "
          f"多源={len(site.multi_source)}个 质检={site.quality_gate}")
    link = spi.mappings.get_link("grass", "treated_by")
    print(f"  treated_by: 物化={link.materialization.value} from={link.from_key} to={link.to_key}")
    assert site.materialization is Materialization.HYBRID
    print("  ✓ 映射加载正确")


if __name__ == "__main__":
    main()
