"""集成验证：把 GraphStore SPI + OQL 真跑在本地 NebulaGraph 上。

前置：docker compose -f deploy/nebula/docker-compose.yml up -d  且 pip install nebula3-python
运行：python scripts/nebula_integration.py

证明：同一套 GraphStore SPI / OQL，换内存后端为 NebulaGraph adapter，内核与插件零改动。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.query import QueryView, StagedLink
from clife_onto_engine.query.nebula_store import NebulaGraphStore
from clife_onto_engine.query.oql import Aggregate, Cond, OQLQuery, Step, execute
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401 — 注册 schema（对象/关系/映射）


def main() -> None:
    store = NebulaGraphStore(ontology_id="grass", registry=spi.registry).connect()
    print("== bootstrap space=grass（建库建模，DDL 等待中…）==")
    store.bootstrap(drop=True)

    print("== 写入对象 + 关系（经 nGQL INSERT）==")
    store.put_object("Site", "parcel_001", {"parcel_id": "parcel_001", "region": "巴彦淖尔"})
    store.put_object("Degradation", "deg1", {"deg_id": "deg1", "level": "重度", "type": "盐渍化"})
    store.put_object("RestorationMethod", "m_喷播", {"method_id": "m_喷播", "name": "喷播"})
    store.put_object("RestorationMethod", "m_补播", {"method_id": "m_补播", "name": "补播"})
    store.put_object("SeedPack", "sp1", {"pack_id": "sp1", "name": "盐碱灌草包"})
    store.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg1"))
    store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_喷播", {"applicability": 0.9}))
    store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_补播", {"applicability": 0.6}))
    store.put_link(StagedLink("uses", "RestorationMethod", "m_喷播", "SeedPack", "sp1"))

    print("== get_object / search_around（经 nGQL FETCH / GO）==")
    print(f"  get Site parcel_001: {store.get_object('Site', 'parcel_001')}")
    hits = store.search_around("Degradation", "deg1", "treated_by")
    print(f"  deg1 -treated_by-> {[(h.node_key, h.node.get('name'), h.edge_props) for h in hits]}")
    rev = store.search_around("RestorationMethod", "m_喷播", "treated_by", direction="in")
    print(f"  反向 in: {[(h.node_type, h.node_key) for h in rev]}")

    print("== 同一 OQL（与内存后端逐字相同）跑在 NebulaGraph 上 ==")
    view = QueryView(store, [])
    q = OQLQuery(
        namespace="grass", start="Site", where=(Cond("region", "eq", "巴彦淖尔"),),
        steps=(Step("suffers"), Step("treated_by"), Step("uses")), select=("name",),
    )
    r = execute(q, view, spi.registry)
    print(f"  多跳到种子包 rows={r.rows} 成本={r.cost}")
    q3 = OQLQuery(
        namespace="grass", start="Site", where=(Cond("region", "eq", "巴彦淖尔"),),
        steps=(Step("suffers"), Step("treated_by")), aggregate=Aggregate("count"),
    )
    print(f"  聚合·修复方法数 {execute(q3, view, spi.registry).rows}")

    store.close()
    print("== OK：GraphStore SPI + OQL 在真实 NebulaGraph 上跑通 ==")


if __name__ == "__main__":
    main()
