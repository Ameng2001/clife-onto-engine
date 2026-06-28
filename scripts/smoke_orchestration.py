"""冒烟：多智能体编排 —— 共享记忆 IPC + Router 最小权限 + DAG，末端落到真 Action 引擎。

三智能体管线（意图→规划→执行），彼此只经分层记忆交接，不传消息：
  intent(读/写 CONTEXT) → plan(读 CRITICAL/RULE/CONTEXT，写 CONTEXT) → act(读 CONTEXT，写 CONTEXT；调引擎)

运行：  python scripts/smoke_orchestration.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.memory import Layer, MemoryItem, MemoryStore
from clife_onto_engine.orchestration import AgentResult, AgentSpec, Orchestrator, SharedMemory
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, CapabilityError, spi

from plugins.grass import seed_reference_data

NS, SID = "grass", "sess-001"
L = Layer


def _structured(ctx, tag):
    """从可读记忆里取出带某 tag 的结构化交接（共享记忆 IPC）。"""
    for it in ctx.recall({tag}).items:
        if tag in it.tags:
            return json.loads(it.content)
    return None


def build_agents(engine: ActionEngine, actor: Actor) -> list[AgentSpec]:
    def intent_fn(ctx) -> AgentResult:
        # 把 NL/表单意图规范化为结构化意图，写入 CONTEXT（不传消息，落记忆）
        intent = {"action": "出一地一方", "site_id": ctx.intent["site_id"],
                  "species": ctx.intent["species"], "budget": ctx.intent["budget"]}
        ctx.remember(L.CONTEXT, json.dumps(intent, ensure_ascii=False),
                     tags=("intent",), source="user")
        return AgentResult("done", {"intent": intent})

    def plan_fn(ctx) -> AgentResult:
        rec = ctx.recall({"intent", "约束"})
        crit = [it.text() for it in rec.items if it.layer == L.CRITICAL]
        intent = _structured(ctx, "intent")
        plan = {"action": intent["action"],
                "params": {"site_id": intent["site_id"], "species": intent["species"],
                           "budget": intent["budget"]}}
        ctx.remember(L.CONTEXT, json.dumps(plan, ensure_ascii=False), tags=("plan",))
        return AgentResult("done", {"saw_critical": crit, "plan": plan})

    def act_fn(ctx) -> AgentResult:
        plan = _structured(ctx, "plan")
        res = engine.execute(NS, plan["action"], plan["params"], actor,
                             schema_version="grass@0.1.0", ts="2026-06-28T15:00:00")
        outcome = {"committed": res.committed,
                   "detail": getattr(res, "written", None) or
                             [v.rule for v in getattr(res, "violations", ())]}
        ctx.remember(L.CONTEXT, json.dumps(outcome, ensure_ascii=False),
                     tags=("action_result",), source="action_result")
        return AgentResult("done", outcome)

    return [
        AgentSpec("intent", frozenset({L.CONTEXT}), frozenset({L.CONTEXT}), intent_fn),
        AgentSpec("plan", frozenset({L.CRITICAL, L.RULE, L.CONTEXT}), frozenset({L.CONTEXT}),
                  plan_fn, depends_on=("intent",)),
        AgentSpec("act", frozenset({L.CONTEXT}), frozenset({L.CONTEXT}), act_fn,
                  depends_on=("plan",)),
    ]


def main() -> None:
    # 引擎 + 草业参考数据（让乡土合规可判定）
    gstore = InMemoryStore()
    seed_reference_data(gstore)
    engine = ActionEngine(spi.registry, store=gstore)
    actor = Actor(id="u1", role="施工方")

    # 共享记忆 + 一条 CRITICAL 约束（供 plan 看到）
    mem = MemoryStore()
    mem.add(MemoryItem(id=f"{SID}:crit1", ontology_id=NS, session_id=SID, layer=L.CRITICAL,
                       content="本盟市修复必须乡土合规、播量在品种区间内"))
    shared = SharedMemory(mem, NS, SID)
    orch = Orchestrator(shared)

    print("== 三智能体管线（合规种子包）→ 期望 act committed ==")
    results = orch.run(build_agents(engine, actor),
                       intent={"site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300})
    print(f"  plan 看到的 CRITICAL 约束: {results['plan'].data['saw_critical']}")
    print(f"  act 结果: {results['act'].data}")
    print(f"  共享记忆条数（IPC 留痕）: intent/plan/result 均落 CONTEXT = "
          f"{len(mem.by_layer(L.CONTEXT, NS, SID))} 条")

    print("== Router 最小权限：act 越权写 RULE → 拒绝 ==")
    def rogue_fn(ctx):
        ctx.remember(L.RULE, "我想偷改规则")   # act 只允许写 CONTEXT
        return AgentResult("done")
    rogue = [AgentSpec("act", frozenset({L.CONTEXT}), frozenset({L.CONTEXT}), rogue_fn)]
    try:
        Orchestrator(SharedMemory(MemoryStore(), NS, SID)).run(rogue, intent={})
    except CapabilityError as e:
        print(f"  ✓ 拦截: {e}")

    print("== DAG 环依赖 → 报错 ==")
    a = AgentSpec("a", frozenset(), frozenset(), lambda c: AgentResult("done"), depends_on=("b",))
    b = AgentSpec("b", frozenset(), frozenset(), lambda c: AgentResult("done"), depends_on=("a",))
    try:
        Orchestrator(shared).run([a, b], intent={})
    except ValueError as e:
        print(f"  ✓ 检出: {e}")


if __name__ == "__main__":
    main()
