"""集成验证：to_ngql 真翻译 —— 在真 NebulaGraph 上对齐 execute()（proven SPI 路径）。

这是 to_ngql"真翻译"的**执行等价性证明**：同一 OQL，
  · 走 execute()（SPI: find_where + search_around，已被 nebula_integration/pushdown 验证）；
  · 走 to_ngql() 编译的**整条 nGQL**，交 nebula session 直接执行。
逐查询断言两者结果一致（锚点/OR 组比 vid 集，多跳比条数，count 比数值）。

前置：docker compose -f deploy/nebula/docker-compose.yml up -d  且 pip install nebula3-python
运行：python scripts/nebula_to_ngql.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.query import QueryView, StagedLink
from clife_onto_engine.query.nebula_store import NebulaGraphStore
from clife_onto_engine.query.oql import Aggregate, Cond, OQLQuery, Or, Step, execute, to_ngql
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401

R = spi.registry


def _ngql_vids(store, ngql: str) -> list:
    res = store._exec(ngql)
    return [res.row_values(i)[0].as_string() for i in range(res.row_size())]


def _ngql_count(store, ngql: str) -> int:
    res = store._exec(ngql)
    return res.row_values(0)[0].as_int() if res.row_size() else 0


def main() -> int:
    store = NebulaGraphStore(ontology_id="grass", registry=R).connect()
    print("== bootstrap space=grass（建库建模）==")
    store.bootstrap(drop=True)

    # 播种：3 地块（2 巴彦淖尔 + 1 乌兰察布）+ 修复主干
    for pid, region in (("p1", "巴彦淖尔"), ("p2", "巴彦淖尔"), ("p3", "乌兰察布")):
        store.put_object("Site", pid, {"parcel_id": pid, "region": region, "site_type": "盐碱"})
        store.put_object("Degradation", f"d{pid}", {"deg_id": f"d{pid}", "level": "重度"})
        store.put_link(StagedLink("suffers", "Site", pid, "Degradation", f"d{pid}"))
    view = QueryView(store, [])

    fails = 0

    def check(name, q, mode):
        nonlocal fails
        ngql = to_ngql(q, R)
        if mode == "vids":
            got = set(_ngql_vids(store, ngql))
            pk = R.mappings.get_object("grass", q.start).primary.key
            exp = {r[pk] for r in execute(q, view, R).rows}
        elif mode == "count_rows":                 # 多跳：比条数
            got = len(_ngql_vids(store, ngql))
            exp = len(execute(q, view, R).rows)
        else:                                      # count 聚合：比数值
            got = _ngql_count(store, ngql)
            exp = execute(q, view, R).rows[0]["count"]
        ok = got == exp
        fails += not ok
        print(f"  {'✓' if ok else '✗'} {name}: to_ngql={got} vs execute={exp}")
        if not ok:
            print(f"      nGQL: {ngql}")

    print("== 逐查询对齐 to_ngql vs execute() ==")
    # 1 锚点·原生列 WHERE（select pk 便于比 vid）
    check("锚点 region=巴彦淖尔",
          OQLQuery(namespace="grass", start="Site", where=(Cond("region", "eq", "巴彦淖尔"),),
                   select=("parcel_id",)), "vids")
    # 2 OR 组
    check("OR region∈{巴彦淖尔,乌兰察布}",
          OQLQuery(namespace="grass", start="Site",
                   where=(Or((Cond("region", "eq", "巴彦淖尔"), Cond("region", "eq", "乌兰察布"))),),
                   select=("parcel_id",)), "vids")
    # 3 多跳
    check("多跳 Site→suffers→Degradation",
          OQLQuery(namespace="grass", start="Site", where=(Cond("region", "eq", "巴彦淖尔"),),
                   steps=(Step("suffers", "out"),)), "count_rows")
    # 4 count 聚合
    check("count 全量地块",
          OQLQuery(namespace="grass", start="Site", aggregate=Aggregate("count")), "count_agg")

    store.close()
    if fails:
        print(f"\n✗ to_ngql 真翻译交叉验证失败（{fails}）"); return 1
    print("\n✓ to_ngql 真翻译：整条 nGQL 在真集群与 execute() SPI 路径逐查询一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
