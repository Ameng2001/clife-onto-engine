"""记忆条目与四层定义（类比 CPU 多级缓存）。

与行业无关：内核只管"哪层、何时淘汰、装进多少 token"，不管记忆内容属于哪个行业。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Layer(str, Enum):
    CRITICAL = "CRITICAL"      # L1：硬约束，永不驱逐，全量注入不过滤
    RULE = "RULE"              # L2：当前任务相关规则，动态加载
    CONTEXT = "CONTEXT"        # L3：近期对话工作状态，滑动窗口
    BACKGROUND = "BACKGROUND"  # MainMem：背景知识，按需换入


# 注入优先级（数字小=先保）。CRITICAL 永远最先、且不丢。
LAYER_PRIORITY = {Layer.CRITICAL: 0, Layer.RULE: 1, Layer.CONTEXT: 2, Layer.BACKGROUND: 3}


class Lifecycle(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


ALIVE = {Lifecycle.HOT, Lifecycle.WARM, Lifecycle.COLD}


@dataclass
class MemoryItem:
    id: str
    ontology_id: str
    session_id: str
    layer: Layer
    content: str
    compressed: str = ""              # 压缩态（CRITICAL/RULE 优先用，省 token）
    confidence: float = 1.0
    hit_count: int = 0
    lifecycle: Lifecycle = Lifecycle.HOT
    tags: tuple[str, ...] = ()
    source: str = ""                  # schema | user | action_result | expert ...
    bound_entity: str = ""            # 绑定的 Rule 名 / 对象类型 / Action（供级联淘汰）
    schema_version: str = ""
    seq: int = 0                      # 单调递增，用于 CONTEXT 滑动窗口的"近期"判定

    @property
    def alive(self) -> bool:
        return self.lifecycle in ALIVE

    def text(self) -> str:
        """注入用文本：有压缩态优先用压缩态。"""
        return self.compressed or self.content
