"""规则变更影响分析（B2）—— 上线前评估"这次本体变更会翻转哪些历史决策"。

建在决策重放（replay.py）之上：对一批历史决策的 inputs，用**同一 store** 分别对
旧/新本体版本各重放一次，diff 裁决。同 store/同 inputs → 差异**只来自版本（规则）变更**，
从而隔离出规则改动本身的影响（排除数据漂移）。这让"变更可评估"从口号变可测。

与行业无关（CI 强制）。边界继承 replay：function-backed 规则读调用方传入的 store。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .replay import replay


@dataclass(frozen=True)
class Flip:
    ontology_id: str
    action: str
    direction: str              # newly_blocked | newly_allowed
    triggering_rules: tuple     # 导致差异的规则名
    original_decision: str


@dataclass(frozen=True)
class ImpactReport:
    total: int
    unchanged: int
    skipped: int
    flips: tuple[Flip, ...] = ()

    @property
    def newly_blocked(self) -> list["Flip"]:
        return [f for f in self.flips if f.direction == "newly_blocked"]

    @property
    def newly_allowed(self) -> list["Flip"]:
        return [f for f in self.flips if f.direction == "newly_allowed"]

    @property
    def summary(self) -> str:
        return (f"变更影响：共 {self.total} 条 · 新拦 {len(self.newly_blocked)} · "
                f"新放 {len(self.newly_allowed)} · 不变 {self.unchanged} · 跳过 {self.skipped}")


def change_impact(snapshots, old_registry, new_registry, *, store=None) -> ImpactReport:
    """对一批审计快照，同 store 分别对旧/新版本重放并 diff。"""
    flips: list[Flip] = []
    unchanged = skipped = 0
    for s in snapshots:
        ro = replay(s, old_registry, store=store)
        rn = replay(s, new_registry, store=store)
        if ro.skipped or rn.skipped:
            skipped += 1
            continue
        if ro.replay_would_commit == rn.replay_would_commit:
            unchanged += 1
            continue
        if ro.replay_would_commit and not rn.replay_would_commit:
            # 旧会提交、新被拦 → 新版哪条规则拦的
            flips.append(Flip(s.ontology_id, s.action, "newly_blocked",
                              tuple(v.rule for v in rn.violations), s.decision))
        else:
            # 旧被拦、新放开 → 原先哪条规则拦、现在放开
            flips.append(Flip(s.ontology_id, s.action, "newly_allowed",
                              tuple(v.rule for v in ro.violations), s.decision))
    # 每个快照恰好落入一个桶 → total = 三桶之和（对生成器输入也正确）
    return ImpactReport(total=unchanged + skipped + len(flips),
                        unchanged=unchanged, skipped=skipped, flips=tuple(flips))
