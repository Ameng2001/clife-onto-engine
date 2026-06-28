"""ActionContext —— 内核内部的 Action 运行态（changeset / effects / confidence / evidence）。

注意：**插件不直接拿到 ActionContext**。内核把它包进 `Capability`（capability.py）再交给
插件的 handler / rule / function。ActionContext 上的方法是内核内部 API；能力收窄与
越权拦截在 Capability 层完成。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..query import QueryView


@dataclass(frozen=True)
class Actor:
    id: str
    role: str


@dataclass
class Effect:
    type: str               # workitem | webhook | notify | schedule ...
    payload: dict = field(default_factory=dict)
    on: Optional[str] = None


class ActionContext:
    def __init__(self, *, ontology_id: str, params: dict, actor: Actor,
                 view: QueryView, overlay: list) -> None:
        self.ontology_id = ontology_id
        self.params = dict(params)
        self.actor = actor
        self.view = view              # 只读视图（base ∪ overlay）
        self._changeset: list = overlay  # 与 view 的 overlay 同引用 → 写即可见
        self._effects: list[Effect] = []
        self._confidence: float = 1.0
        self._evidence: list[dict] = []

    # ---- 内核内部写入（由 Capability 经校验后调用）----
    def _stage(self, op) -> None:
        self._changeset.append(op)

    def _add_effect(self, e: Effect) -> None:
        self._effects.append(e)

    def _set_confidence(self, value: float) -> None:
        self._confidence = max(0.0, min(1.0, value))

    def _add_evidence(self, d: dict) -> None:
        self._evidence.append(dict(d))

    # ---- 内核读取 ----
    @property
    def changeset(self) -> list:
        return list(self._changeset)

    @property
    def effects(self) -> list[Effect]:
        return list(self._effects)

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def evidence(self) -> list[dict]:
        return list(self._evidence)
