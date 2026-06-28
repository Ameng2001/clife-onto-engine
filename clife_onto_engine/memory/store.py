"""记忆存储与淘汰（生命周期状态机 + 置信度衰减 + 规则变更级联）。

按 (ontology_id, session_id) 隔离。骨架用内存；落地可换持久层（同接口）。
"""
from __future__ import annotations

from typing import Iterable, Optional

from .item import Layer, Lifecycle, MemoryItem

DECAY_ON_FAILURE = 0.2
DEPRECATE_BELOW = 0.3


class MemoryStore:
    def __init__(self) -> None:
        self._items: dict[str, MemoryItem] = {}
        self._seq = 0

    def add(self, item: MemoryItem) -> MemoryItem:
        self._seq += 1
        item.seq = self._seq
        self._items[item.id] = item
        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        return self._items.get(item_id)

    def by_layer(self, layer: Layer, ontology_id: str, session_id: str,
                 *, alive_only: bool = True) -> list[MemoryItem]:
        out = [
            it for it in self._items.values()
            if it.layer == layer and it.ontology_id == ontology_id
            and it.session_id == session_id and (it.alive or not alive_only)
        ]
        return out

    # ---- 访问：命中即升温 ----
    def access(self, item_id: str) -> None:
        it = self._items.get(item_id)
        if it:
            it.hit_count += 1
            it.lifecycle = Lifecycle.HOT

    # ---- 淘汰：置信度衰减（操作失败回流）----
    def record_action_outcome(self, item_ids: Iterable[str], success: bool) -> None:
        if success:
            return
        for iid in item_ids:
            it = self._items.get(iid)
            if not it:
                continue
            it.confidence = round(max(0.0, it.confidence - DECAY_ON_FAILURE), 4)
            if it.confidence < DEPRECATE_BELOW:
                it.lifecycle = Lifecycle.DEPRECATED

    # ---- 淘汰：规则变更级联（旧记忆立即作废）----
    def on_rule_change(self, ontology_id: str, rule_name: str) -> int:
        n = 0
        for it in self._items.values():
            if (it.ontology_id == ontology_id and it.bound_entity == rule_name
                    and it.layer in (Layer.RULE, Layer.CRITICAL) and it.alive):
                it.lifecycle = Lifecycle.DEPRECATED
                n += 1
        return n

    # ---- 生命周期降温（可周期调用）----
    def demote_stale(self, ontology_id: str, session_id: str, cold_below_hits: int = 1) -> None:
        for it in self._items.values():
            if it.ontology_id != ontology_id or it.session_id != session_id:
                continue
            if it.layer == Layer.CRITICAL:
                continue  # CRITICAL 不降温
            if it.hit_count <= cold_below_hits and it.lifecycle == Lifecycle.HOT:
                it.lifecycle = Lifecycle.WARM
            elif it.lifecycle == Lifecycle.WARM:
                it.lifecycle = Lifecycle.COLD
