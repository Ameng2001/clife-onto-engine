"""遥测经口语触达：意图编译器认 telemetry kind → Session 产查询计划（不执行）。

序列须在声明的遥测绑定内（防注入，不接受清单外名字）。此前遥测只能经 /plan 端点直达，
口语'parcel_001 墒情怎么样'到不了；本组测试锁住 NL→telemetry→build_plan 回路。
"""
from clife_onto_engine.intent.compiler import CompiledIntent, IntentCompiler
from clife_onto_engine.intent.manifest import build_manifest, render_manifest
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

import plugins.grass  # noqa: F401


class _Client:
    """桩 LLM：complete_json 直接返回预置 raw。"""
    def __init__(self, raw):
        self._raw = raw

    def complete_json(self, system, user):
        return self._raw


class _FixedCompiler:
    def __init__(self, ci):
        self._ci = ci

    def compile(self, *a, **k):
        return self._ci


def _store():
    s = InMemoryStore()
    s.put_object("Site", "parcel_001", {"parcel_id": "parcel_001", "region": "巴彦淖尔", "site_type": "盐碱"})
    return s


def _session(ci):
    return Session(ontology_id="grass", registry=spi.registry, store=_store(),
                   compiler=_FixedCompiler(ci), actor=Actor("u", "施工方"), schema_version="grass@0.1.0")


# ---- Session 路由 ----

def test_telemetry_intent_produces_plan():
    ci = CompiledIntent("telemetry", confidence=0.9, tele_object="Site",
                        tele_key="parcel_001", tele_series="soil_moisture")
    r = _session(ci).ask("parcel_001 墒情怎么样")
    assert r.kind == "telemetry"
    assert r.plan["provider"] == "prometheus"
    assert 'parcel="parcel_001"' in r.plan["plan"]     # 实例 id 已代入模板


def test_telemetry_log_series_with_params():
    ci = CompiledIntent("telemetry", confidence=0.9, tele_object="Site", tele_key="parcel_001",
                        tele_series="iot_alerts", tele_params={"level": "error", "since": "now-1h"})
    r = _session(ci).ask("parcel_001 最近有什么告警")
    assert r.kind == "telemetry" and r.plan["provider"] == "elasticsearch" and r.plan["kind"] == "log"


# ---- 编译器校验（防注入）----

def _compile(raw):
    return IntentCompiler(_Client(raw), spi.registry).compile("grass", "x")


def test_compile_valid_telemetry():
    ci = _compile({"kind": "telemetry", "confidence": 0.9,
                   "telemetry": {"object": "Site", "key": "parcel_001", "series": "soil_moisture"}})
    assert ci.kind == "telemetry" and ci.tele_series == "soil_moisture" and ci.tele_key == "parcel_001"


def test_compile_unknown_series_rejected():
    ci = _compile({"kind": "telemetry", "confidence": 0.9,
                   "telemetry": {"object": "Site", "key": "parcel_001", "series": "偷偷加的"}})
    assert ci.kind == "reject" and "清单外遥测序列" in ci.error


def test_compile_unknown_object_rejected():
    ci = _compile({"kind": "telemetry", "confidence": 0.9,
                   "telemetry": {"object": "NoSuch", "key": "x", "series": "soil_moisture"}})
    assert ci.kind == "reject" and "无遥测绑定" in ci.error


def test_compile_missing_key_clarifies():
    ci = _compile({"kind": "telemetry", "confidence": 0.9,
                   "telemetry": {"object": "Site", "series": "soil_moisture"}})
    assert ci.kind == "clarify"


# ---- manifest 暴露遥测 ----

def test_manifest_exposes_telemetry():
    m = build_manifest(spi.registry, "grass")
    assert any(t["object"] == "Site" for t in m["telemetry"])
    assert "可观测遥测" in render_manifest(m)
