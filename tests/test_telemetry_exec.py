"""遥测执行回路：离线执行器 + Session"看指标"端到端出值 + 无执行器时计划-only 兼容。"""
from __future__ import annotations

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.telemetry import InMemoryTelemetryExecutor, build_plan
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def test_build_plan_now_carries_object_key_series():
    plan = build_plan(spi.registry, _seeded(), "Site", "parcel_001", "soil_moisture", namespace="grass")
    assert plan["ok"] and plan["object"] == "Site" and plan["key"] == "parcel_001"
    assert plan["series"] == "soil_moisture" and "parcel_001" in plan["plan"]


def test_executor_metric_value_log_points_and_missing():
    ex = InMemoryTelemetryExecutor()
    ex.put("Site", "soil_moisture", "parcel_001", 23.5)
    ex.put("Site", "iot_alerts", "parcel_001", [{"ts": "t1", "msg": "超载"}])
    plan_m = build_plan(spi.registry, _seeded(), "Site", "parcel_001", "soil_moisture", namespace="grass")
    assert ex.execute(plan_m) == {"ok": True, "provider": plan_m["provider"], "kind": "metric",
                                  "plan": plan_m["plan"], "value": 23.5}
    plan_l = build_plan(spi.registry, _seeded(), "Site", "parcel_001", "iot_alerts",
                        namespace="grass", params={"level": "warn", "since": "2026-07-01"})
    out = ex.execute(plan_l)
    assert out["ok"] and out["kind"] == "log" and out["points"] == [{"ts": "t1", "msg": "超载"}]
    # 无 seeded 数据 → 结构化错误（不崩）
    plan_n = build_plan(spi.registry, _seeded(), "Site", "parcel_001", "ndvi_30d", namespace="grass")
    assert ex.execute(plan_n)["ok"] is False


class _TeleStub:
    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        return CompiledIntent("telemetry", confidence=0.9, tele_object="Site",
                              tele_key="parcel_001", tele_series="soil_moisture", tele_params={})


def test_session_telemetry_returns_value_with_executor():
    ex = InMemoryTelemetryExecutor({("Site", "soil_moisture", "parcel_001"): 23.5})
    session = Session(ontology_id="grass", registry=spi.registry, store=_seeded(),
                      compiler=_TeleStub(), actor=Actor("u1", "牧民"), telemetry_executor=ex)
    reply = session.ask("parcel_001 这块地墒情多少？")
    assert reply.kind == "telemetry" and reply.value == 23.5
    assert reply.plan and reply.plan["ok"]           # 计划仍在（可溯）
    assert "23.5" in reply.summary()


def test_session_telemetry_plan_only_without_executor():
    """未接执行器 → 仅返回计划（向后兼容）。"""
    session = Session(ontology_id="grass", registry=spi.registry, store=_seeded(),
                      compiler=_TeleStub(), actor=Actor("u1", "牧民"))
    reply = session.ask("parcel_001 这块地墒情多少？")
    assert reply.kind == "telemetry" and reply.value is None and reply.plan["ok"]
