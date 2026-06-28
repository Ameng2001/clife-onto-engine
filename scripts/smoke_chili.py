"""冒烟：辣椒插件 —— 证明"换行业零改内核"。

同一套 Action 引擎 + 意图编译器 + 记忆/编排，跑辣椒域；内核未改一行。
与 grass 在同一 registry 按 namespace 共存（双本体最小形态）。

运行（A/B/C/D 离线；E 需 llm.local.json）：python scripts/smoke_chili.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi

import plugins.chili as chili
import plugins.grass  # noqa: F401 — 双本体共存：grass 也在同一 registry

NS = "chili"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    store = InMemoryStore()
    chili.seed_reference_data(store)
    engine = ActionEngine(spi.registry, store=store)
    grower = Actor("u1", "种植户")

    print("== 双本体共存（同一 registry，namespace 隔离）==")
    acts = sorted(name for (ns, name) in spi.registry.actions if ns == "chili")
    grass_acts = sorted(name for (ns, name) in spi.registry.actions if ns == "grass")
    print(f"  chili Actions: {acts}")
    print(f"  grass Actions: {grass_acts}（同进程互不干扰）")

    print("\n== A. 适配品种 → commit ==")
    a = engine.execute(NS, "制定种植方案",
                       {"field_id": "field_001", "variety": "朝天椒", "density": 2000, "budget": 500},
                       grower, schema_version="chili@0.1.0", ts="2026-06-28T18:00:00")
    print(f"  committed={a.committed} written={getattr(a,'written',None)}")
    print(f"  读回 PlantingPlan: {store.get_object('PlantingPlan', 'plan_field_001')}")

    print("== B. 非适配品种(紫色甜椒) → 写后回滚拒绝 ==")
    s2 = InMemoryStore(); chili.seed_reference_data(s2)
    b = ActionEngine(spi.registry, store=s2).execute(
        NS, "制定种植方案",
        {"field_id": "field_001", "variety": "紫色甜椒", "density": 2000, "budget": 500},
        grower, schema_version="chili@0.1.0", ts="2026-06-28T18:01:00")
    print(f"  committed={b.committed} 违反={[v.rule for v in getattr(b,'violations',())]}")
    print(f"  回滚验证: {s2.get_object('PlantingPlan', 'plan_field_001')}")

    print("== C. 辣椒分级·优质 → 等级落库 ==")
    c = engine.execute(NS, "辣椒分级",
                       {"batch_id": "CB01", "measurements": {"length": 14, "SHU": 50000, "defect_rate": 0.01}},
                       grower, schema_version="chili@0.1.0", ts="2026-06-28T18:02:00")
    sample = store.get_object("GradeSample", "CB01") or {}
    print(f"  committed={c.committed} 等级={sample.get('grade')} 溯源码={sample.get('trace_code')}")

    print("== D. 残次率超标 → 回滚拒绝 ==")
    d = engine.execute(NS, "辣椒分级",
                       {"batch_id": "CB02", "measurements": {"length": 10, "SHU": 30000, "defect_rate": 0.30}},
                       grower, schema_version="chili@0.1.0", ts="2026-06-28T18:03:00")
    print(f"  committed={d.committed} 违反={[v.rule for v in getattr(d,'violations',())]}")

    # E：同一个意图编译器服务辣椒域（需 LLM）
    cfg = ROOT / "llm.local.json"
    if cfg.exists():
        from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
        print("\n== E. 同一意图编译器跑辣椒口语 → action → commit ==")
        compiler = IntentCompiler(OpenAICompatibleClient(config_path=str(cfg)), spi.registry)
        utt = "我海南的地 field_001 想种朝天椒，每亩2000株，预算500"
        ci = compiler.compile(NS, utt, actor_role="种植户")
        print(f"  「{utt}」→ [{ci.kind}] {ci.action} {ci.params}")
        if ci.executable:
            s3 = InMemoryStore(); chili.seed_reference_data(s3)
            r = ActionEngine(spi.registry, store=s3).execute(NS, ci.action, ci.params, grower,
                                                             schema_version="chili@0.1.0", ts="2026-06-28T18:04:00")
            print(f"  NL→Action: committed={r.committed} written={getattr(r,'written',None)}")
    else:
        print("\n== E 跳过（无 llm.local.json）==")


if __name__ == "__main__":
    main()
