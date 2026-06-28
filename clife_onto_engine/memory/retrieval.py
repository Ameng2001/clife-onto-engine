"""检索与 token 预算装配。

核心纪律（方法论）：**CRITICAL 全量注入、永不过滤、永不丢**；其余层按相关性
（关键词命中 + hit_count×confidence）在各自预算内择优填充，超预算则压缩/丢弃低优先项。
"非整理，而是优先级保证"。

token 估算为可替换的简单实现（CJK 约 1 char≈1 token）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .item import Layer, MemoryItem
from .store import MemoryStore

DEFAULT_BUDGET = {
    Layer.CRITICAL: 200,
    Layer.RULE: 500,
    Layer.CONTEXT: 400,
    Layer.BACKGROUND: 300,
}


def estimate_tokens(text: str) -> int:
    return len(text)


def relevance(item: MemoryItem, keywords: set[str]) -> float:
    hay = (item.content + " " + " ".join(item.tags)).lower()
    hits = sum(1 for k in keywords if k.lower() in hay)
    return hits * 10.0 + item.hit_count * item.confidence


@dataclass
class LayerReport:
    budget: int
    used: int
    included: int
    dropped: int


@dataclass
class AssembledContext:
    items: list[MemoryItem]
    text: str
    report: dict           # Layer -> LayerReport
    total_tokens: int

    def layer_text(self, layer: Layer) -> str:
        return "\n".join(it.text() for it in self.items if it.layer == layer)


def assemble(
    store: MemoryStore,
    ontology_id: str,
    session_id: str,
    keywords: set[str],
    *,
    budget: dict | None = None,
    only_layers: set[Layer] | None = None,
) -> AssembledContext:
    budget = dict(budget or DEFAULT_BUDGET)
    chosen: list[MemoryItem] = []
    report: dict = {}

    for layer in (Layer.CRITICAL, Layer.RULE, Layer.CONTEXT, Layer.BACKGROUND):
        if only_layers is not None and layer not in only_layers:
            continue
        items = store.by_layer(layer, ontology_id, session_id)
        cap = budget.get(layer, 0)

        if layer == Layer.CRITICAL:
            # 全量注入、永不过滤、永不丢（即便超预算也保）
            picked = sorted(items, key=lambda it: it.seq)
            used = sum(estimate_tokens(it.text()) for it in picked)
            chosen.extend(picked)
            report[layer] = LayerReport(cap, used, len(picked), 0)
            continue

        if layer == Layer.CONTEXT:
            # 滑动窗口：按 seq 倒序（最近优先）
            ranked = sorted(items, key=lambda it: it.seq, reverse=True)
        else:
            # RULE / BACKGROUND：按相关性
            ranked = sorted(items, key=lambda it: relevance(it, keywords), reverse=True)

        used, included, dropped = 0, 0, 0
        for it in ranked:
            t = estimate_tokens(it.text())
            if used + t <= cap:
                chosen.append(it)
                used += t
                included += 1
            else:
                dropped += 1
        report[layer] = LayerReport(cap, used, included, dropped)

    chosen.sort(key=lambda it: (it.layer != Layer.CRITICAL, it.seq))  # CRITICAL 置顶
    text = "\n".join(f"[{it.layer.value}] {it.text()}" for it in chosen)
    total = sum(estimate_tokens(it.text()) for it in chosen)
    return AssembledContext(items=chosen, text=text, report=report, total_tokens=total)
