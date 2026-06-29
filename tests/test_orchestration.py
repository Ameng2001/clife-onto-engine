"""多智能体编排：共享记忆 IPC、Router 最小权限、DAG 环检测。"""
from __future__ import annotations

import pytest

from clife_onto_engine.memory import Layer, MemoryStore
from clife_onto_engine.orchestration import AgentResult, AgentSpec, Orchestrator, SharedMemory
from clife_onto_engine.sdk import CapabilityError

NS, SID = "grass", "s1"


def _shared():
    return SharedMemory(MemoryStore(), NS, SID)


def test_shared_memory_ipc():
    shared = _shared()

    def writer(ctx):
        ctx.remember(Layer.CONTEXT, "handoff", tags=("h",))
        return AgentResult("done")

    def reader(ctx):
        items = [it for it in ctx.recall({"h"}).items if "h" in it.tags]
        return AgentResult("done", {"saw": len(items)})

    agents = [
        AgentSpec("w", frozenset(), frozenset({Layer.CONTEXT}), writer),
        AgentSpec("r", frozenset({Layer.CONTEXT}), frozenset(), reader, depends_on=("w",)),
    ]
    res = Orchestrator(shared).run(agents, intent={})
    assert res["r"].data["saw"] == 1                  # 经记忆交接，非传消息


def test_router_least_privilege_blocks_write():
    shared = _shared()

    def rogue(ctx):
        ctx.remember(Layer.RULE, "偷改")              # 只许写 CONTEXT
        return AgentResult("done")

    agents = [AgentSpec("a", frozenset(), frozenset({Layer.CONTEXT}), rogue)]
    with pytest.raises(CapabilityError):
        Orchestrator(shared).run(agents, intent={})


def test_dag_cycle_detected():
    shared = _shared()
    a = AgentSpec("a", frozenset(), frozenset(), lambda c: AgentResult("done"), depends_on=("b",))
    b = AgentSpec("b", frozenset(), frozenset(), lambda c: AgentResult("done"), depends_on=("a",))
    with pytest.raises(ValueError):
        Orchestrator(shared).run([a, b], intent={})
