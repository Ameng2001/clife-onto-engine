"""CQ 验收回路（C3）：套件对当前版本全 pass；版本削弱规则被抓；查询/权限/报告。"""
from __future__ import annotations

from dataclasses import replace

from clife_onto_engine.cq import ActionCQ, QueryCQ, run_cq_suite
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.oql import Cond, OQLQuery
from clife_onto_engine.sdk import spi
from clife_onto_engine.versioning import snapshot_ontology

import plugins.grass  # noqa: F401
from plugins.grass.cq import CQ_SUITE


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def test_suite_passes_current_version():
    rep = run_cq_suite(CQ_SUITE, spi.registry, store=_seeded())
    assert rep.ok and rep.passed == rep.total == 17


def test_regression_caught_when_rule_removed():
    v = snapshot_ontology(spi.registry, "grass", "grass@no-native")
    act = v.registry.actions[("grass", "出一地一方")]
    v.registry.actions[("grass", "出一地一方")] = replace(
        act, post_rules=tuple(r for r in act.post_rules if r != "乡土合规"))
    rep = run_cq_suite(CQ_SUITE, v.registry, store=_seeded())
    assert not rep.ok
    native = next(r for r in rep.results if r.name == "非乡土草种被拦")
    assert not native.passed and "实际 commit" in native.detail


def test_action_cq_expect_rule_specific():
    # 期望被"乡土合规"拦，但实际被别的规则拦（如预算）→ 应 fail（规则不匹配）
    cq = ActionCQ("错规则期望", "grass", "出一地一方",
                  {"site_id": "parcel_001", "species": ["碱茅"], "budget": -1},
                  actor_role="施工方", expect="reject", expect_rule="乡土合规")
    rep = run_cq_suite([cq], spi.registry, store=_seeded())
    # budget=-1 被"预算非负"拦，不是"乡土合规" → CQ 不通过
    assert not rep.ok and not rep.results[0].passed


def test_query_cq_min_rows():
    # 不存在的区域 → 0 行 < 门槛 → fail
    cq = QueryCQ("空区域", "grass",
                 OQLQuery(namespace="grass", start="Site",
                          where=(Cond("region", "eq", "不存在的地"),)), min_rows=1)
    rep = run_cq_suite([cq], spi.registry, store=_seeded())
    assert not rep.results[0].passed and "0 行" in rep.results[0].actual


def test_report_counts_and_summary():
    rep = run_cq_suite(CQ_SUITE, spi.registry, store=_seeded())
    assert rep.total == 17 and "17/17 通过" in rep.summary
