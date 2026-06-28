"""多智能体编排 —— 共享记忆 IPC + Router 最小权限 + DAG 执行。与行业无关。

要点（方法论）：
  - Agent 之间**不传消息**，而是读/写分层记忆（共享记忆即 IPC）——确定、可追溯、语义完整。
  - Router 最小权限：每个 Agent 只能读/写它声明的记忆层；越权抛 CapabilityError。
  - 上下文隔离：recall 只装配该 Agent 可读层（不是全量任务上下文）。
  - DAG：按依赖拓扑执行；环依赖即报错；单 Agent 失败重试，隔离失败。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..memory import AssembledContext, Layer, MemoryItem, MemoryStore, assemble
from ..sdk.errors import CapabilityError


@dataclass(frozen=True)
class AgentResult:
    status: str                       # done | need:<agent> | error
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class AgentSpec:
    name: str
    reads: frozenset                  # frozenset[Layer]
    writes: frozenset                 # frozenset[Layer]
    fn: Callable                      # (AgentContext) -> AgentResult
    depends_on: tuple = ()


class SharedMemory:
    """智能体间的 IPC 总线 = 一份按 (ontology_id, session_id) 隔离的 MemoryStore。"""

    def __init__(self, store: MemoryStore, ontology_id: str, session_id: str) -> None:
        self.store = store
        self.ontology_id = ontology_id
        self.session_id = session_id


class AgentContext:
    """交给 Agent 的受限句柄：recall/remember 受 Router（reads/writes）约束。"""

    def __init__(self, spec: AgentSpec, shared: SharedMemory, intent: dict) -> None:
        self._spec = spec
        self._shared = shared
        self.intent = dict(intent)
        self._n = 0

    @property
    def name(self) -> str:
        return self._spec.name

    def recall(self, keywords) -> AssembledContext:
        """上下文隔离 + 最小权限：只装配本 Agent 可读层。"""
        return assemble(
            self._shared.store, self._shared.ontology_id, self._shared.session_id,
            set(keywords), only_layers=set(self._spec.reads),
        )

    def remember(self, layer: Layer, content: str, *, compressed: str = "",
                 tags: tuple = (), source: str = "", bound_entity: str = "",
                 confidence: float = 1.0) -> MemoryItem:
        if layer not in self._spec.writes:
            raise CapabilityError(
                f"Router 最小权限: Agent {self._spec.name} 不可写 {layer.value}"
            )
        self._n += 1
        item = MemoryItem(
            id=f"{self._shared.session_id}:{self._spec.name}:{self._n}",
            ontology_id=self._shared.ontology_id, session_id=self._shared.session_id,
            layer=layer, content=content, compressed=compressed, tags=tuple(tags),
            source=source, bound_entity=bound_entity, confidence=confidence,
        )
        return self._shared.store.add(item)


class Orchestrator:
    def __init__(self, shared: SharedMemory, *, max_retries: int = 3) -> None:
        self.shared = shared
        self.max_retries = max_retries

    def run(self, agents: list[AgentSpec], intent: dict) -> dict:
        order = _topo_sort(agents)        # 环依赖即抛
        results: dict[str, AgentResult] = {}
        for spec in order:
            ctx = AgentContext(spec, self.shared, intent)
            last_err: Optional[Exception] = None
            for _ in range(self.max_retries):
                try:
                    results[spec.name] = spec.fn(ctx)
                    last_err = None
                    break
                except CapabilityError:
                    raise                  # 越权是确定性错误，不重试
                except Exception as e:     # 失败隔离 + 重试
                    last_err = e
            if last_err is not None:
                results[spec.name] = AgentResult("error", {"error": str(last_err)})
        return results


def _topo_sort(agents: list[AgentSpec]) -> list[AgentSpec]:
    by_name = {a.name: a for a in agents}
    visited: dict[str, int] = {}          # 0=visiting,1=done
    order: list[AgentSpec] = []

    def visit(name: str, stack: tuple) -> None:
        if visited.get(name) == 1:
            return
        if visited.get(name) == 0:
            raise ValueError(f"DAG 存在环依赖: {' -> '.join(stack + (name,))}")
        visited[name] = 0
        for dep in by_name[name].depends_on:
            if dep not in by_name:
                raise ValueError(f"未知依赖: {name} -> {dep}")
            visit(dep, stack + (name,))
        visited[name] = 1
        order.append(by_name[name])

    for a in agents:
        visit(a.name, ())
    return order


__all__ = [
    "AgentSpec", "AgentResult", "AgentContext", "SharedMemory", "Orchestrator",
]
