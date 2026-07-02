"""遥测执行回路 smoke —— 离线演示："看指标"从只产计划到真出值，端到端闭环。

引擎产计划（PromQL/ES，id 已代入、防注入），执行器出值（离线默认读 seeded 序列，
真部署换打 Prometheus/ES 的适配器、同协议）。全离线、无 LLM（桩编译器）。

运行：python scripts/smoke_telemetry_exec.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.telemetry import InMemoryTelemetryExecutor
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


class _TeleStub:
    def __init__(self, series):
        self._series = series

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        return CompiledIntent("telemetry", confidence=0.9, tele_object="Site",
                              tele_key="parcel_001", tele_series=self._series,
                              tele_params={"level": "warn", "since": "2026-07-01"})


def main() -> int:
    store = InMemoryStore(); plugins.grass.seed_reference_data(store)
    ex = InMemoryTelemetryExecutor()
    ex.put("Site", "soil_moisture", "parcel_001", 21.8)     # 墒情 %
    ex.put("Site", "ndvi_30d", "parcel_001", 0.42)          # 近30天 NDVI
    ex.put("Site", "iot_alerts", "parcel_001", [{"ts": "2026-07-02T08:00", "msg": "墒情低于阈值"}])

    print("== 遥测执行回路 smoke（离线）==")
    fails = 0
    for series, q in (("soil_moisture", "parcel_001 墒情多少？"),
                      ("ndvi_30d", "parcel_001 近一个月长势？"),
                      ("iot_alerts", "parcel_001 有什么告警？")):
        s = Session(ontology_id="grass", registry=spi.registry, store=store,
                    compiler=_TeleStub(series), actor=Actor("u1", "牧民"), telemetry_executor=ex)
        reply = s.ask(q)
        ok = reply.kind == "telemetry" and reply.value is not None
        fails += not ok
        print(f"\n  ❓ {q}")
        print(f"     计划（{reply.plan['provider']}/{reply.plan['kind']}，id 已代入）：{reply.plan['plan']}")
        print(f"     {'✓' if ok else '✗'} 出值：{reply.value}")

    # 无执行器 → 仅计划（向后兼容）
    s2 = Session(ontology_id="grass", registry=spi.registry, store=store,
                 compiler=_TeleStub("soil_moisture"), actor=Actor("u1", "牧民"))
    r2 = s2.ask("parcel_001 墒情多少？")
    compat_ok = r2.kind == "telemetry" and r2.value is None and r2.plan["ok"]
    fails += not compat_ok
    print(f"\n  {'✓' if compat_ok else '✗'} 无执行器时仅返回计划（向后兼容）")

    if fails:
        print(f"\n✗ 遥测执行 smoke 失败（{fails}）"); return 1
    print("\n✓ 遥测执行回路 smoke 全通过：引擎产计划 → 执行器出值，端到端闭环 · 无执行器时计划-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
