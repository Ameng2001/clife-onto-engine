"""记忆分层 —— 三维判断（动词特征 / 来源类型 / 绑定实体）。

与行业无关：只看通用模态词与来源类型，不认任何行业概念。
词典可由插件经 SPI 扩充（槽位 5），此处是内核缺省。
"""
from __future__ import annotations

from typing import Optional

from .item import Layer

# 缺省模态词（通用，非行业）。插件可补充自己的词典。
HARD_VERBS = ("必须", "不得", "禁止", "严禁", "强制", "must", "never", "shall not")
SOFT_VERBS = ("建议", "优先", "尽量", "应当", "should", "prefer")


def classify(
    content: str,
    *,
    source: Optional[str] = None,            # schema | user | action_result | expert
    bound_entity_kind: Optional[str] = None,  # Rule | object | action_result
    hard_verbs: tuple[str, ...] = HARD_VERBS,
    soft_verbs: tuple[str, ...] = SOFT_VERBS,
) -> Layer:
    # 维度 1：动词特征（最强信号）
    if any(v in content for v in hard_verbs):
        return Layer.CRITICAL
    # 维度 3：绑定实体
    if bound_entity_kind == "Rule":
        return Layer.RULE
    if bound_entity_kind == "action_result":
        return Layer.CONTEXT
    # 维度 2：来源类型
    if source == "schema":
        return Layer.RULE
    if source == "user":
        return Layer.CONTEXT
    # 维度 1 弱信号
    if any(v in content for v in soft_verbs):
        return Layer.RULE
    return Layer.BACKGROUND
