"""Capability 越界运行时审计：越界→回滚+审计+结构化拒绝（不崩）；validate 捕获；合法不受影响。"""
from __future__ import annotations

import pytest

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


@pytest.fixture
def breach_action():
    def _breach(ctx):
        ctx.stage_write("SeedPack", "x", {})   # 未声明 writes → 越界
    spi.registry.actions[("grass", "_breach")] = ActionDef(
        name="_breach", namespace="grass", writes=(), validate_supported=True, impl=_breach)
    yield "_breach"
    del spi.registry.actions[("grass", "_breach")]


def test_breach_rolled_back_audited_rejected(breach_action):
    store = InMemoryStore()
    eng = ActionEngine(spi.registry, store=store)
    res = eng.execute("grass", breach_action, {}, Actor("u", "施工方"), schema_version="v")
    assert not res.committed and res.phase == "capability"
    assert store.get_object("SeedPack", "x") is None                 # 确定性回滚
    assert eng.audit.query("grass")[-1].decision == "capability_violation"  # 留痕
    assert any(v.rule == "capability" for v in res.violations)


def test_validate_catches_breach(breach_action):
    eng = ActionEngine(spi.registry, store=InMemoryStore())
    prev = eng.validate("grass", breach_action, {}, Actor("u", "施工方"))
    assert not prev.would_commit and any(v.rule == "capability" for v in prev.violations)


def test_legal_action_unaffected():
    from clife_onto_engine.query import InMemoryStore as S
    store = S(); plugins.grass.seed_reference_data(store)
    eng = ActionEngine(spi.registry, store=store)
    res = eng.execute("grass", "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                      Actor("u1", "施工方"), schema_version="v")
    assert res.committed                                             # 合法动作照常
