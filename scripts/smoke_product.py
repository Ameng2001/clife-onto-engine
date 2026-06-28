"""冒烟：端到端产品回路 —— 一句口语 → 多智能体（编译→执行）→ 真 commit。

把意图编译器(真 Qwen)嵌进编排：intent 智能体编译 NL（带四层记忆接地），
act 智能体交给真 Action 引擎执行；两者只经分层记忆交接。Action 引擎自带
guard/写后规则/回滚 = 确定性验证器，故无独立 SimAgent。

前置：llm.local.json + docker 无关（用内存图后端）
运行：python scripts/smoke_product.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient, make_action_agent, make_intent_agent
from clife_onto_engine.memory import Layer, MemoryItem, MemoryStore
from clife_onto_engine.orchestration import Orchestrator, SharedMemory
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi

from plugins.grass import seed_reference_data

NS = "grass"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def run_once(utterance: str, role: str, *, compiler, engine, label: str) -> None:
    print(f"\n== {label} ==\n  用户「{utterance}」（{role}）")
    sid = f"sess-{abs(hash(utterance)) % 10000}"
    mem = MemoryStore()
    # 一条 CRITICAL 约束做记忆接地（intent 编译时会看到）
    mem.add(MemoryItem(id=f"{sid}:crit", ontology_id=NS, session_id=sid, layer=Layer.CRITICAL,
                       content="本盟市修复必须乡土合规、播量在品种区间内"))
    shared = SharedMemory(mem, NS, sid)
    actor = Actor("u1", role)

    agents = [
        make_intent_agent(compiler, NS),
        make_action_agent(engine, NS, actor=actor, schema_version="grass@0.1.0", ts="2026-06-28T17:00:00"),
    ]
    results = Orchestrator(shared).run(agents, intent={"utterance": utterance, "actor_role": role})

    intent_r, act_r = results["intent"], results["act"]
    print(f"  intent[{intent_r.status}] conf={intent_r.data.get('confidence')} "
          f"→ {intent_r.data.get('action') or intent_r.data.get('question')}")
    print(f"  act[{act_r.status}] → {act_r.data}")
    print(f"  共享记忆 CONTEXT 留痕: {len(mem.by_layer(Layer.CONTEXT, NS, sid))} 条（intent + result）")


def main() -> None:
    compiler = IntentCompiler(OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json")),
                              spi.registry)
    gstore = InMemoryStore()
    seed_reference_data(gstore)
    engine = ActionEngine(spi.registry, store=gstore)
    print(f"模型: {compiler.client.model}")

    run_once("我家盐碱地 parcel_001 想低成本修复，用碱茅和披碱草，预算每亩300", "施工方",
             compiler=compiler, engine=engine, label="A. 合规口语 → 期望 commit")
    run_once("给我修复一下草场吧", "牧民",
             compiler=compiler, engine=engine, label="B. 信息不足 → 期望 act 跳过 + 追问")
    run_once("我这块地 parcel_001 用紫花苜蓿修复，预算每亩300", "施工方",
             compiler=compiler, engine=engine, label="C. 非乡土草种 → 编译成 action 但引擎回滚拒绝")


if __name__ == "__main__":
    main()
