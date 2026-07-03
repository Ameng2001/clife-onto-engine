"""遥测读 Profile B（数仓/分析读）smoke —— 语义指标 → 数仓 SQL → DuckDB 维度化聚合。

监管场景："某盟市近年盖度趋势"：声明式语义指标(度量+维度+过滤)编译成数仓 SQL、跑在 DuckDB。
与 Profile A(观测遥测·单序列) 分工；分析读走虚拟递数仓。运行：python scripts/smoke_analytical_read.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.query.telemetry import build_analytical_plan
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401


def main() -> int:
    try:
        from clife_onto_engine.query.duckdb_telemetry import DuckDBTelemetryExecutor
    except Exception as e:  # pragma: no cover
        print(f"跳过：需 pip install duckdb（{e}）"); return 0

    ex = DuckDBTelemetryExecutor()
    ex.conn.execute("CREATE TABLE rs_monitor(region VARCHAR, year INT, coverage DOUBLE)")
    ex.conn.execute("INSERT INTO rs_monitor VALUES "
                    "('巴彦淖尔',2022,0.35),('巴彦淖尔',2023,0.42),('巴彦淖尔',2024,0.51),"
                    "('乌兰察布',2024,0.88)")
    ex.conn.execute("CREATE TABLE geo_parcel(parcel_id VARCHAR, region VARCHAR)")
    ex.conn.execute("INSERT INTO geo_parcel VALUES ('p1','巴彦淖尔'),('p2','巴彦淖尔'),('p3','乌兰察布')")

    print("== 遥测读 Profile B（数仓/分析读）smoke ==")
    fails = 0
    for metric, params, label in (("退化趋势", {"region": "巴彦淖尔"}, "近年盖度趋势"),
                                  ("区域地块数", {"region": "巴彦淖尔"}, "地块计数")):
        plan = build_analytical_plan(spi.registry, "grass", metric, params=params)
        out = ex.execute(plan)
        ok = out.get("ok")
        fails += not ok
        print(f"\n  📊 语义指标「{metric}」· {label}（{params}）")
        print(f"     编译数仓 SQL：{plan['plan']}")
        print(f"     {'✓' if ok else '✗'} DuckDB 维度化结果：{out.get('points')}")

    # 防注入：恶意过滤值在产计划层被拒
    bad = build_analytical_plan(spi.registry, "grass", "退化趋势",
                                params={"region": "x'; DROP TABLE rs_monitor;--"})
    inj_ok = bad["ok"] is False
    fails += not inj_ok
    print(f"\n  {'✓' if inj_ok else '✗'} 防注入：恶意过滤值被产计划层拒（{bad.get('error','')[:20]}…）")

    if fails:
        print(f"\n✗ Profile B smoke 失败（{fails}）"); return 1
    print("\n✓ Profile B smoke 全通过：语义指标→数仓 SQL→维度化聚合，防注入在产计划层")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
