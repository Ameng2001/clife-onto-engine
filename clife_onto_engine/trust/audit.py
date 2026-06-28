"""审计快照 —— 存"快照"而非"变更"，落地"过程可溯、结果可验"。

每次 Action 裁决落一条不可变记录：AI 当时看到的输入、评估了哪些规则及结果、
最终裁决、置信度、证据链、所用 schema 版本。支持回溯查询：
「用当时的 schema_version，这个操作合法吗」。

骨架用内存 append-only 列表；落地替换为 JSONL / 对象库（见 docs §5.1、方法论 Software 3.0）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RuleEvaluation:
    rule: str
    result: str            # pass | violate
    backing: str           # declarative | function
    severity: str          # hard | soft
    message: str = ""


@dataclass(frozen=True)
class AuditSnapshot:
    ontology_id: str
    action: str
    actor_id: str
    actor_role: str
    inputs_snapshot: dict
    rules_evaluated: tuple[RuleEvaluation, ...]
    decision: str          # committed | rejected | pending_hil
    confidence: float
    evidence: tuple[dict, ...]
    schema_version: str
    ts: Optional[str] = None  # 由调用方注入（内核不调用 wall clock）

    def to_dict(self) -> dict:
        return {
            "ontology_id": self.ontology_id,
            "action": self.action,
            "actor": {"id": self.actor_id, "role": self.actor_role},
            "inputs_snapshot": self.inputs_snapshot,
            "rules_evaluated": [r.__dict__ for r in self.rules_evaluated],
            "decision": self.decision,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "schema_version": self.schema_version,
            "ts": self.ts,
        }


class AuditStore:
    """append-only。按 ontology_id 隔离查询。"""

    def __init__(self) -> None:
        self._records: list[AuditSnapshot] = []

    def record(self, snap: AuditSnapshot) -> None:
        self._records.append(snap)

    def query(self, ontology_id: str) -> list[AuditSnapshot]:
        return [r for r in self._records if r.ontology_id == ontology_id]

    def __len__(self) -> int:
        return len(self._records)
