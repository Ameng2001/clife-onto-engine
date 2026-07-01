"""规则变更影响分析 smoke（B2）——上线前评估"这次改规则会翻转哪些历史决策"。

一批 grass 历史决策，对"预算门槛 300→500"的新版本做影响分析：
精确列出**被新拦**的决策 + 触发规则「预算非负」；对更宽版本列出**被新放**的。全离线。
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.change_impact import change_impact
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import RuleResult, spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.versioning import snapshot_ontology

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def _budget_rule(threshold):
    def _f(ctx):
        b = ctx.params.get("budget", 0)
        return RuleResult.ok() if (b is not None and b >= threshold) else RuleResult.fail(f"预算需≥{threshold}")
    return _f


def _version(threshold):
    v = snapshot_ontology(spi.registry, "grass", f"grass@budget{threshold}")
    orig = v.registry.rules[("grass", "预算非负")]
    v.registry.rules[("grass", "预算非负")] = replace(orig, impl=_budget_rule(threshold))
    return v.registry


def _batch_snapshots():
    """3 条合规草种、不同预算的历史决策（budget 300/450/600），原都按"≥0"通过 committed。"""
    snaps = []
    for i, budget in enumerate((300, 450, 600)):
        eng = ActionEngine(spi.registry, store=_seeded())
        eng.execute("grass", "出一地一方",
                    {"site_id": "parcel_001", "species": ["碱茅"], "budget": budget},
                    Actor(f"u{i}", "施工方"), schema_version="grass@lax")
        snaps.append(eng.audit.query("grass")[-1])
    return snaps


def main() -> int:
    fails = 0
    snaps = _batch_snapshots()
    old = _version(0)      # 旧：预算≥0（都过）
    strict = _version(500) # 新严：预算≥500 → 300/450 被拦，600 过

    rep = change_impact(snaps, old, strict, store=_seeded())
    print("==", rep.summary, "==")
    ok = (len(rep.newly_blocked) == 2 and len(rep.newly_allowed) == 0 and rep.unchanged == 1
          and all("预算非负" in f.triggering_rules for f in rep.newly_blocked))
    print(f"== 更严版本→新拦2条（触发规则 预算非负）：{'✓' if ok else '✗ ' + str(rep.flips)} ==")
    fails += not ok

    # 反向：从严版本 → 更宽版本，原被拦的现放开
    rep2 = change_impact(snaps, strict, _version(0), store=_seeded())
    ok2 = len(rep2.newly_allowed) == 2 and len(rep2.newly_blocked) == 0
    print(f"== 放宽版本→新放2条：{'✓' if ok2 else '✗ ' + str(rep2.flips)} ==")
    fails += not ok2

    # 无变更：old vs old
    rep3 = change_impact(snaps, old, _version(0), store=_seeded())
    ok3 = rep3.unchanged == 3 and not rep3.flips
    print(f"== 无变更→全不变：{'✓' if ok3 else '✗'} ==")
    fails += not ok3

    if fails:
        print(f"\n✗ 变更影响 smoke 失败（{fails}）"); return 1
    print("\n✓ 规则变更影响分析 smoke 全通过：新拦/新放/不变精确归类 + 触发规则可读")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
