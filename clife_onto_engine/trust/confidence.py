"""置信度总线（骨架）。

跨层传播 confidence，并在裁决时给出诊断方向：
  - 低置信被拒 → 多半是意图编译器理解错（上游）
  - 高置信被拒 → 触发记忆/规则审计（本体侧可能有陈旧规则）

HIL 路由不靠人肉判断，由 confidence 阈值 + 是否触碰 hard 规则决定（见 HilPolicy）。
"""
from __future__ import annotations

LOW_CONFIDENCE = 0.5


class ConfidenceBus:
    @staticmethod
    def diagnose_rejection(confidence: float) -> str:
        if confidence < LOW_CONFIDENCE:
            return "low_confidence:意图理解可能有误，建议回 IntentAgent 复核"
        return "high_confidence:本体侧拒绝，建议审计规则/记忆是否陈旧"

    @staticmethod
    def should_route_hil(hil, confidence: float, touched_hard: bool) -> bool:
        if hil is None:
            return False
        return bool(hil.predicate(confidence, touched_hard))
