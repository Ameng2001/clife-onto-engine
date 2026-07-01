"""决策重放 —— 用审计快照存的 inputs，对指定本体版本只读重跑裁决。

治理化变更生命周期的地基（路线图 B/C 共享）：复用 `ActionEngine.validate()`（无副作用预演），
把 `AuditSnapshot` 存的 params/actor 喂回去，复现/对比裁决；支持 param 覆盖做**反事实**
（"换个入参会怎样"）。是规则变更影响分析（B2）、CQ 验收（C3）的共享原语。

范围边界（诚实）：guard（declarative）从存储 inputs **忠实复现**；function-backed 规则读
**调用方传入的 store**（默认空）。忠实的点位历史 store 重放留后续扩展。

与行业无关（CI 强制）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .kernel import ActionEngine
from .query import InMemoryStore
from .sdk.context import Actor


@dataclass(frozen=True)
class ReplayResult:
    ontology_id: str
    action: str
    original_decision: str          # committed | rejected | pending_hil
    replay_would_commit: Optional[bool]
    flipped: bool                   # 原裁决与重放是否翻转
    violations: tuple               # 重放命中的 Violation
    counterfactual: bool            # 是否用了 param 覆盖
    against_version: Optional[str] = None
    skipped: bool = False
    skip_reason: str = ""

    @property
    def summary(self) -> str:
        if self.skipped:
            return f"[跳过] {self.action}：{self.skip_reason}"
        tag = "翻转" if self.flipped else "复现"
        cf = "（反事实）" if self.counterfactual else ""
        return (f"[{tag}{cf}] {self.action}：原={self.original_decision} · "
                f"重放 would_commit={self.replay_would_commit} · "
                f"违反={[v.rule for v in self.violations]}")


def _would_commit(decision: str) -> bool:
    return decision in ("committed", "pending_hil")


def replay(snapshot, registry, *, store=None, param_overrides: Optional[dict] = None,
           against_version: Optional[str] = None) -> ReplayResult:
    """用 AuditSnapshot 的 inputs 对 registry（活的或某版本）只读重放 validate。

    snapshot: AuditSnapshot（有 ontology_id/action/actor_id/actor_role/inputs_snapshot/decision）
    registry: 目标 registry —— 活的 spi.registry，或某 OntologyVersion.registry
    store:    function-backed 规则用的 store（默认空）；反事实/变更影响可传当前 store
    param_overrides: 覆盖部分参数做反事实（如换某个入参值）
    """
    actor = Actor(snapshot.actor_id, snapshot.actor_role)
    # inputs_snapshot = {"params": {...}, "actor": {...}}（见 ActionEngine._snapshot）
    params = dict(snapshot.inputs_snapshot.get("params", {}))
    if param_overrides:
        params.update(param_overrides)
    engine = ActionEngine(registry, store=store if store is not None else InMemoryStore())

    try:
        preview = engine.validate(snapshot.ontology_id, snapshot.action, params, actor)
    except Exception as e:  # validate_supported=False / 未注册 → 结构化跳过
        return ReplayResult(
            ontology_id=snapshot.ontology_id, action=snapshot.action,
            original_decision=snapshot.decision, replay_would_commit=None,
            flipped=False, violations=(), counterfactual=bool(param_overrides),
            against_version=against_version, skipped=True, skip_reason=f"{type(e).__name__}: {e}",
        )

    flipped = _would_commit(snapshot.decision) != preview.would_commit
    return ReplayResult(
        ontology_id=snapshot.ontology_id, action=snapshot.action,
        original_decision=snapshot.decision, replay_would_commit=preview.would_commit,
        flipped=flipped, violations=tuple(preview.violations),
        counterfactual=bool(param_overrides), against_version=against_version,
    )
