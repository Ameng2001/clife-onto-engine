"""结构化拒绝与裁决结果。

铁律：拒绝是**结构化数据，不是异常**。返回触发的规则、当前状态快照、建议调整，
供 Agent 自动重试（在合规候选集内改了再试）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..trust.audit import RuleEvaluation


@dataclass(frozen=True)
class Violation:
    rule: str
    severity: str          # hard | soft
    backing: str
    message: str = ""
    suggestion: str = ""


@dataclass(frozen=True)
class StructuredRejection:
    ontology_id: str
    action: str
    phase: str             # guard | post_write
    violations: tuple[Violation, ...]
    state_snapshot: dict
    diagnosis: str = ""

    @property
    def committed(self) -> bool:
        return False


@dataclass(frozen=True)
class ActionResult:
    ontology_id: str
    action: str
    decision: str          # committed | pending_hil
    written: tuple[tuple[str, str], ...]  # (object_type, key)
    effects_scheduled: tuple[str, ...]
    confidence: float
    hil_required: bool = False
    advisory: tuple[Violation, ...] = ()   # soft 违反（不阻断，但记录）
    # 已提交关系 (link_type, from_type, from_key, to_type, to_key)——供读层反映；默认空，向后兼容
    links_written: tuple[tuple[str, str, str, str, str], ...] = ()

    @property
    def committed(self) -> bool:
        return True


@dataclass(frozen=True)
class ActionPreview:
    """validate 预演结果：无副作用，永不落库。"""
    ontology_id: str
    action: str
    would_commit: bool
    staged: tuple[tuple[str, str], ...]
    violations: tuple[Violation, ...]
    confidence: float
