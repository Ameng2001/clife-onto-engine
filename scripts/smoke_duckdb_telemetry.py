"""DuckDB 遥测执行器 smoke —— 真 SQL 后端出值，却零服务器（嵌入式）。

引擎产已代入 SQL（防注入在 build_plan），DuckDBTelemetryExecutor 在进程内 DuckDB 真跑出值。
与离线 InMemory 执行器同协议——Session 换后端无感。运行：python scripts/smoke_duckdb_telemetry.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.duckdb_telemetry import DuckDBTelemetryExecutor
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


class _Stub:
    def compile(self, ns, utt, *, memory_text="", actor_role=None):
        return CompiledIntent("telemetry", confidence=0.9, tele_object="Site",
                              tele_key="parcel_001", tele_series="soil_moisture_db", tele_params={})


def main() -> int:
    store = InMemoryStore(); plugins.grass.seed_reference_data(store)
    ex = DuckDBTelemetryExecutor()                       # 进程内 DuckDB，无服务器
    ex.conn.execute("CREATE TABLE iot_soil(parcel VARCHAR, moisture DOUBLE)")
    ex.conn.execute("INSERT INTO iot_soil VALUES "
                    "('parcel_001', 20.0), ('parcel_001', 24.0), ('parcel_002', 51.0)")

    print("== DuckDB 遥测 smoke（嵌入式真后端）==")
    session = Session(ontology_id="grass", registry=spi.registry, store=store,
                      compiler=_Stub(), actor=Actor("u1", "牧民"), telemetry_executor=ex)
    reply = session.ask("parcel_001 墒情多少？")
    ok = reply.kind == "telemetry" and reply.value == 22.0
    print(f"  计划（{reply.plan['provider']}，id 已代入、防注入）：{reply.plan['plan']}")
    print(f"  {'✓' if ok else '✗'} DuckDB 真跑出值：{reply.value}（avg 20,24；parcel_002 未混入）")

    # 防注入：恶意 label 在 build_plan 就被拒，SQL 永不成型
    bad = InMemoryStore()
    bad.put_object("Site", "x'; DROP TABLE iot_soil;--",
                   {"parcel_id": "x'; DROP TABLE iot_soil;--", "region": "x", "site_type": "盐碱", "area_mu": 1})
    from clife_onto_engine.query.telemetry import build_plan
    p = build_plan(spi.registry, bad, "Site", "x'; DROP TABLE iot_soil;--", "soil_moisture_db", namespace="grass")
    inj_ok = p["ok"] is False
    print(f"  {'✓' if inj_ok else '✗'} 防注入：恶意 label 被 build_plan 拦下（{p.get('error','')[:24]}…）")

    if not (ok and inj_ok):
        print("\n✗ DuckDB 遥测 smoke 失败"); return 1
    print("\n✓ DuckDB 遥测 smoke 全通过：真 SQL 后端出值、零服务器、防注入在产计划层")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
