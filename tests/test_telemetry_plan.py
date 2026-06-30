"""遥测 query-plan：声明绑定 → 生成可执行计划（不执行）、防注入、缺字段结构化拒绝。"""
from __future__ import annotations

from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.telemetry import build_plan
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401  (含遥测绑定)


def _store():
    s = InMemoryStore()
    plugins.grass.seed_reference_data(s)
    return s


def test_binding_loaded():
    b = spi.registry.mappings.get_telemetry("grass", "Site")
    assert b is not None and b.provider == "prometheus"
    assert {s.name for s in b.series} >= {"soil_moisture", "ndvi_30d"}


def test_plan_substitutes_instance_id():
    r = build_plan(spi.registry, _store(), "Site", "parcel_001", "soil_moisture", namespace="grass")
    assert r["ok"] and r["provider"] == "prometheus"
    assert r["plan"] == 'avg(soil_moisture_percent{parcel="parcel_001"})'
    assert r["resolved_labels"] == {"parcel": "parcel_001"}
    assert r["cost"] == {"telemetry-plan": 1}


def test_engine_only_builds_plan_no_execution():
    # build_plan 返回计划串，不含任何"执行/结果"——引擎不当 TSDB
    r = build_plan(spi.registry, _store(), "Site", "parcel_001", "ndvi_30d", namespace="grass")
    assert r["ok"] and "$parcel" not in r["plan"] and "[30d]" in r["plan"]
    assert "result" not in r and "value" not in r  # 只产计划，无数据


def test_missing_label_field_structured_error():
    s = _store(); s.put_object("Site", "bad", {"region": "x"})
    r = build_plan(spi.registry, s, "Site", "bad", "soil_moisture", namespace="grass")
    assert not r["ok"] and "parcel_id" in r["error"]


def test_injection_blocked():
    s = _store(); s.put_object("Site", "inj", {"parcel_id": '"} or up{'})
    r = build_plan(spi.registry, s, "Site", "inj", "soil_moisture", namespace="grass")
    assert not r["ok"] and "防注入" in r["error"]


def test_unknown_series_and_binding():
    r = build_plan(spi.registry, _store(), "Site", "parcel_001", "nope", namespace="grass")
    assert not r["ok"] and "序列" in r["error"]
    r2 = build_plan(spi.registry, _store(), "NativeListing", "x", "m", namespace="grass")
    assert not r2["ok"] and "未声明遥测绑定" in r2["error"]
