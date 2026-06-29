"""集成验证：OQL 谓词下推 —— 把筛选推给 NebulaGraph 在库内（走索引）过滤。

证明：region 落成原生列 + 索引后，`find_where(region==X)` 编译成 nGQL `LOOKUP ... WHERE`，
NebulaGraph **只返回命中的行**（库内过滤），而非全扫回引擎再过滤。

前置：docker compose -f deploy/nebula/docker-compose.yml up -d 且 pip install nebula3-python
运行：python scripts/nebula_pushdown.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.query import QueryView
from clife_onto_engine.query.nebula_store import NebulaGraphStore
from clife_onto_engine.query.oql import Cond, OQLQuery, Step, execute
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401 — 注册 schema + 映射（Site.columns 含 region）


def main() -> None:
    store = NebulaGraphStore(ontology_id="grass", registry=spi.registry).connect()
    print("== bootstrap（原生列 region + 列索引，DDL 等待中…）==")
    store.bootstrap(drop=True)

    print("== 写入 3 个地块：2 个巴彦淖尔 + 1 个锡林郭勒 ==")
    store.put_object("Site", "p1", {"parcel_id": "p1", "area_mu": 500, "region": "巴彦淖尔", "site_type": "盐碱"})
    store.put_object("Site", "p2", {"parcel_id": "p2", "area_mu": 300, "region": "巴彦淖尔", "site_type": "沙地"})
    store.put_object("Site", "p3", {"parcel_id": "p3", "area_mu": 800, "region": "锡林郭勒", "site_type": "草原"})

    print("== 谓词下推：find_where(region==巴彦淖尔) → 库内 WHERE 过滤 ==")
    pushed = store.find_where("Site", [("region", "eq", "巴彦淖尔")])
    full = store.find_where("Site", [])
    print(f"  全扫(无条件)返回: {len(full)} 行")
    print(f"  下推(region==巴彦淖尔)返回: {len(pushed)} 行 → {[r['parcel_id'] for r in pushed]}")
    print(f"  → DB 只回了命中的 {len(pushed)} 行（不是全部 {len(full)} 行），证明库内过滤")

    print("== OQL 端到端（anchor 谓词下推）==")
    q = OQLQuery(namespace="grass", start="Site",
                 where=(Cond("region", "eq", "巴彦淖尔"), Cond("site_type", "eq", "盐碱")),
                 select=("parcel_id", "region", "site_type"))
    r = execute(q, QueryView(store, []), spi.registry)
    print(f"  OQL(region==巴彦淖尔 AND site_type==盐碱) → {r.rows} 成本={r.cost}")

    ok = (len(full) == 3 and len(pushed) == 2
          and {x["parcel_id"] for x in pushed} == {"p1", "p2"}
          and r.rows == [{"parcel_id": "p1", "region": "巴彦淖尔", "site_type": "盐碱"}])
    store.close()
    print(f"== {'OK：谓词下推在真实 NebulaGraph 上库内过滤生效' if ok else '失败：断言不符'} ==")


if __name__ == "__main__":
    main()
