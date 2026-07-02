"""DuckDB 遥测执行器：真跑 SQL 出值 + Session 端到端 + 错误兜底 + 防注入仍在 build_plan。"""
from __future__ import annotations

import pytest

duckdb = pytest.importorskip("duckdb")  # 未装 duckdb 则跳过（可选依赖）

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.duckdb_telemetry import DuckDBTelemetryExecutor
from clife_onto_engine.query.telemetry import build_plan
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def _executor_with_data():
    ex = DuckDBTelemetryExecutor()
    ex.conn.execute("CREATE TABLE iot_soil(parcel VARCHAR, moisture DOUBLE)")
    ex.conn.execute("INSERT INTO iot_soil VALUES ('parcel_001', 20), ('parcel_001', 24), ('parcel_002', 50)")
    return ex


def test_duckdb_executor_metric_avg():
    ex = _executor_with_data()
    plan = build_plan(spi.registry, _seeded(), "Site", "parcel_001", "soil_moisture_db", namespace="grass")
    assert plan["ok"] and plan["provider"] == "sql" and "parcel_001" in plan["plan"]
    out = ex.execute(plan)
    assert out["ok"] and out["value"] == 22.0        # avg(20,24)，parcel_002 未混入


def test_session_duckdb_end_to_end():
    ex = _executor_with_data()

    class _Stub:
        def compile(self, ns, utt, *, memory_text="", actor_role=None):
            return CompiledIntent("telemetry", confidence=0.9, tele_object="Site",
                                  tele_key="parcel_001", tele_series="soil_moisture_db", tele_params={})

    session = Session(ontology_id="grass", registry=spi.registry, store=_seeded(),
                      compiler=_Stub(), actor=Actor("u1", "牧民"), telemetry_executor=ex)
    reply = session.ask("parcel_001 墒情多少？")
    assert reply.kind == "telemetry" and reply.value == 22.0 and reply.plan["ok"]


def test_missing_table_returns_structured_error():
    ex = DuckDBTelemetryExecutor()  # 空库，无 iot_soil
    plan = build_plan(spi.registry, _seeded(), "Site", "parcel_001", "soil_moisture_db", namespace="grass")
    out = ex.execute(plan)
    assert out["ok"] is False and "duckdb" in out["error"]


def test_anti_injection_blocked_before_execution():
    """label 值含非法字符 → build_plan 直接拒（防注入在产计划层，SQL 永不成型）。"""
    store = InMemoryStore()
    store.put_object("Site", "p'; DROP TABLE iot_soil;--",
                     {"parcel_id": "p'; DROP TABLE iot_soil;--", "region": "x", "site_type": "盐碱", "area_mu": 1})
    plan = build_plan(spi.registry, store, "Site", "p'; DROP TABLE iot_soil;--",
                      "soil_moisture_db", namespace="grass")
    assert plan["ok"] is False and "防注入" in plan["error"]
