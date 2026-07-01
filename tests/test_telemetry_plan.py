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
    assert b is not None
    assert {s.name for s in b.series} >= {"soil_moisture", "ndvi_30d", "iot_alerts"}
    # provider 在 series 级：metric→prometheus、log→elasticsearch
    by = {s.name: s for s in b.series}
    assert by["soil_moisture"].provider == "prometheus"
    assert by["iot_alerts"].provider == "elasticsearch" and by["iot_alerts"].kind == "log"


def test_es_log_plan_with_runtime_params():
    r = build_plan(spi.registry, _store(), "Site", "parcel_001", "iot_alerts",
                   namespace="grass", params={"level": "ERROR", "since": "now-1h"})
    assert r["ok"] and r["provider"] == "elasticsearch" and r["kind"] == "log"
    assert '"parcel":"parcel_001"' in r["plan"]       # 对象 label 代入
    assert '"level":"ERROR"' in r["plan"]             # 运行时 param 代入
    assert '"gte":"now-1h"' in r["plan"] and "$" not in r["plan"]
    assert r["resolved_params"] == {"level": "ERROR", "since": "now-1h"}


def test_same_build_plan_multi_provider():
    s = _store()
    m = build_plan(spi.registry, s, "Site", "parcel_001", "soil_moisture", namespace="grass")
    l = build_plan(spi.registry, s, "Site", "parcel_001", "iot_alerts",
                   namespace="grass", params={"level": "WARN", "since": "now-1d"})
    assert m["provider"] == "prometheus" and l["provider"] == "elasticsearch"  # 同一 build_plan，两方言


def test_unresolved_placeholder_rejected():
    # 不传 params → $level/$since 无从解析 → 结构化拒绝
    r = build_plan(spi.registry, _store(), "Site", "parcel_001", "iot_alerts", namespace="grass")
    assert not r["ok"] and "未解析占位" in r["error"]


def test_runtime_param_injection_blocked():
    r = build_plan(spi.registry, _store(), "Site", "parcel_001", "iot_alerts",
                   namespace="grass", params={"level": '"} or 1', "since": "now-1h"})
    assert not r["ok"] and "防注入" in r["error"]


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
