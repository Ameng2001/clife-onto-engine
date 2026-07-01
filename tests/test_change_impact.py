"""规则变更影响分析（B2）：新拦/新放/不变精确归类 + 触发规则 + skip。"""
from __future__ import annotations

from dataclasses import replace

from clife_onto_engine.change_impact import change_impact
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import RuleResult, spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.trust.audit import AuditSnapshot
from clife_onto_engine.versioning import snapshot_ontology

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def _version(threshold):
    v = snapshot_ontology(spi.registry, "grass", f"grass@b{threshold}")
    orig = v.registry.rules[("grass", "预算非负")]

    def _f(ctx):
        b = ctx.params.get("budget", 0)
        return RuleResult.ok() if (b is not None and b >= threshold) else RuleResult.fail("预算不足")
    v.registry.rules[("grass", "预算非负")] = replace(orig, impl=_f)
    return v.registry


def _snaps(budgets):
    out = []
    for i, b in enumerate(budgets):
        eng = ActionEngine(spi.registry, store=_seeded())
        eng.execute("grass", "出一地一方",
                    {"site_id": "parcel_001", "species": ["碱茅"], "budget": b},
                    Actor(f"u{i}", "施工方"), schema_version="grass@lax")
        out.append(eng.audit.query("grass")[-1])
    return out


def test_stricter_version_newly_blocks_with_rule():
    snaps = _snaps([300, 450, 600])
    rep = change_impact(snaps, _version(0), _version(500), store=_seeded())
    assert len(rep.newly_blocked) == 2 and rep.unchanged == 1 and not rep.newly_allowed
    assert all("预算非负" in f.triggering_rules for f in rep.newly_blocked)
    assert all(f.direction == "newly_blocked" for f in rep.newly_blocked)


def test_relaxed_version_newly_allows():
    snaps = _snaps([300, 450, 600])
    rep = change_impact(snaps, _version(500), _version(0), store=_seeded())
    assert len(rep.newly_allowed) == 2 and not rep.newly_blocked


def test_no_change_all_unchanged():
    snaps = _snaps([300, 600])
    rep = change_impact(snaps, _version(0), _version(0), store=_seeded())
    assert rep.unchanged == 2 and not rep.flips and rep.total == 2


def test_unsupported_action_skipped():
    spi.registry.actions[("grass", "_nv")] = ActionDef(
        name="_nv", namespace="grass", validate_supported=False)
    try:
        snap = AuditSnapshot(
            ontology_id="grass", action="_nv", actor_id="u", actor_role="施工方",
            inputs_snapshot={"params": {}, "actor": {"id": "u", "role": "施工方"}},
            rules_evaluated=(), decision="committed", confidence=1.0, evidence=(),
            schema_version="x")
        rep = change_impact([snap], _version(0), _version(500), store=_seeded())
        assert rep.skipped == 1 and rep.total == 1 and not rep.flips
    finally:
        del spi.registry.actions[("grass", "_nv")]


def test_report_summary_counts():
    snaps = _snaps([300, 450, 600])
    rep = change_impact(snaps, _version(0), _version(500), store=_seeded())
    assert rep.total == 3 and "新拦 2" in rep.summary
