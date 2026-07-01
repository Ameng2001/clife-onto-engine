"""本体版本化 + 决策重放：快照可执行/不可变/多版本；重放复现/反事实/版本敏感/skip。"""
from __future__ import annotations

from dataclasses import replace

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.replay import replay
from clife_onto_engine.sdk import RuleResult, spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.versioning import OntologyVersionStore, snapshot_ontology

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore()
    plugins.grass.seed_reference_data(s)
    return s


def _committed_snapshot():
    engine = ActionEngine(spi.registry, store=_seeded())
    engine.execute("grass", "出一地一方",
                   {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                   Actor("u1", "施工方"), schema_version="grass@0.1.0")
    return engine.audit.query("grass")[-1]


# ---- 版本化 ----
def test_snapshot_is_executable():
    v = snapshot_ontology(spi.registry, "grass", "grass@0.1.0")
    assert v.registry.get_action("grass", "出一地一方").name == "出一地一方"
    eng = ActionEngine(v.registry, store=_seeded())
    prev = eng.validate("grass", "出一地一方",
                        {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                        Actor("u1", "施工方"))
    assert prev.would_commit


def test_version_immutable():
    v = snapshot_ontology(spi.registry, "grass", "grass@0.1.0")
    spi.registry.actions[("grass", "_probe")] = ActionDef(name="_probe", namespace="grass")
    try:
        assert ("grass", "_probe") not in v.registry.actions       # 快照冻结，不回溯污染
    finally:
        del spi.registry.actions[("grass", "_probe")]


def test_multi_version_coexist():
    store = OntologyVersionStore()
    store.snapshot(spi.registry, "grass", "grass@0.1.0")
    store.snapshot(spi.registry, "grass", "grass@0.2.0")
    assert store.get("grass", "grass@0.1.0") is not None
    assert store.get("grass", "grass@0.2.0") is not None
    assert {v.version for v in store.list("grass")} >= {"grass@0.1.0", "grass@0.2.0"}


# ---- 重放 ----
def test_replay_reproduces():
    snap = _committed_snapshot()
    r = replay(snap, spi.registry, store=_seeded())
    assert r.replay_would_commit and not r.flipped and not r.counterfactual


def test_counterfactual_flips():
    snap = _committed_snapshot()
    r = replay(snap, spi.registry, store=_seeded(),
               param_overrides={"species": ["紫花苜蓿"]})
    assert r.flipped and not r.replay_would_commit and r.counterfactual
    assert any(v.rule == "乡土合规" for v in r.violations)


def test_version_sensitivity():
    snap = _committed_snapshot()  # budget=300, 原 committed
    v = snapshot_ontology(spi.registry, "grass", "grass@strict")
    orig = v.registry.rules[("grass", "预算非负")]

    def _ge500(ctx):
        b = ctx.params.get("budget", 0)
        return RuleResult.ok() if (b is not None and b >= 500) else RuleResult.fail("预算需≥500")
    v.registry.rules[("grass", "预算非负")] = replace(orig, impl=_ge500)

    r = replay(snap, v.registry, store=_seeded(), against_version="grass@strict")
    assert r.flipped and not r.replay_would_commit and r.against_version == "grass@strict"


def test_unsupported_action_skips():
    # 构造一个 validate_supported=False 的动作快照场景：直接伪造一个 AuditSnapshot
    from clife_onto_engine.trust.audit import AuditSnapshot
    spi.registry.actions[("grass", "_noval")] = ActionDef(
        name="_noval", namespace="grass", validate_supported=False)
    try:
        snap = AuditSnapshot(
            ontology_id="grass", action="_noval", actor_id="u1", actor_role="施工方",
            inputs_snapshot={"params": {}, "actor": {"id": "u1", "role": "施工方"}},
            rules_evaluated=(), decision="committed", confidence=1.0, evidence=(),
            schema_version="grass@0.1.0")
        r = replay(snap, spi.registry, store=_seeded())
        assert r.skipped and r.skip_reason
    finally:
        del spi.registry.actions[("grass", "_noval")]
