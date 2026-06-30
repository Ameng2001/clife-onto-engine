"""遥测 query-plan 离线 smoke —— 内化"深读"的遥测侧（无网络、无后端、无 LLM）。

证明：对象 + 声明绑定 → 引擎生成可执行 PromQL 计划（id 已代入）、provider 正确、不触网；
缺 label 字段结构化拒绝；注入式 label 值被拦。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.telemetry import build_plan
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401  (含遥测绑定加载)


def main() -> int:
    store = InMemoryStore()
    plugins.grass.seed_reference_data(store)  # Site/parcel_001
    fails = 0

    # 1) 正例：生成 PromQL，parcel_001 代入、provider=prometheus、无网络
    r = build_plan(spi.registry, store, "Site", "parcel_001", "soil_moisture", namespace="grass")
    ok1 = (r.get("ok") and r["provider"] == "prometheus"
           and 'parcel="parcel_001"' in r["plan"] and "$parcel" not in r["plan"])
    print(f"== 生成 PromQL 计划：{'✓ ' + r.get('plan','') if ok1 else '✗ ' + str(r)} ==")
    fails += not ok1

    # 2) 第二个序列（NDVI）也按模板代入
    r2 = build_plan(spi.registry, store, "Site", "parcel_001", "ndvi_30d", namespace="grass")
    ok2 = r2.get("ok") and 'parcel="parcel_001"' in r2["plan"] and "[30d]" in r2["plan"]
    print(f"== 多序列（NDVI）：{'✓' if ok2 else '✗ ' + str(r2)} ==")
    fails += not ok2

    # 3) 缺 label 字段 → 结构化拒绝（造一个没有 parcel_id 的实例）
    store.put_object("Site", "bad", {"region": "x"})
    r3 = build_plan(spi.registry, store, "Site", "bad", "soil_moisture", namespace="grass")
    ok3 = (not r3.get("ok")) and "parcel_id" in r3.get("error", "")
    print(f"== 缺 label 字段被拒：{'✓' if ok3 else '✗ ' + str(r3)} ==")
    fails += not ok3

    # 4) 注入式 label 值 → 被拦（防注入）
    store.put_object("Site", "inj", {"parcel_id": '"} or up{'})
    r4 = build_plan(spi.registry, store, "Site", "inj", "soil_moisture", namespace="grass")
    ok4 = (not r4.get("ok")) and "防注入" in r4.get("error", "")
    print(f"== 注入式 label 被拦：{'✓' if ok4 else '✗ ' + str(r4)} ==")
    fails += not ok4

    if fails:
        print(f"\n✗ 遥测 query-plan smoke 失败（{fails}）"); return 1
    print("\n✓ 遥测 query-plan smoke 全通过：引擎只产计划（PromQL）、id 代入、防注入、不触网")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
