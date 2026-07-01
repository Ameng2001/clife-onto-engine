"""本体治理缺口审计（C1 运行时侧）：grass 无 blocking；残缺缺口精确定位；advisory。"""
from __future__ import annotations

from dataclasses import replace

from clife_onto_engine.gaps import audit_gaps
from clife_onto_engine.metamodel import ActionDef, LinkType, RuleDef
from clife_onto_engine.sdk import spi
from clife_onto_engine.versioning import snapshot_ontology

import plugins.grass  # noqa: F401


def test_grass_no_blocking():
    rep = audit_gaps(spi.registry, "grass")
    assert rep.ok and not rep.blocking


def test_advisory_reports_missing_source():
    rep = audit_gaps(spi.registry, "grass")
    # declarative guard 无 source → advisory
    assert any(g.kind == "rule_no_source" for g in rep.advisory)
    assert rep.ok  # advisory 不影响 ok


def test_action_no_handler_located():
    v = snapshot_ontology(spi.registry, "grass", "grass@nohandler")
    act = v.registry.actions[("grass", "出一地一方")]
    v.registry.actions[("grass", "出一地一方")] = replace(act, impl=None)
    rep = audit_gaps(v.registry, "grass")
    assert not rep.ok
    g = next(g for g in rep.blocking if g.kind == "action_no_handler")
    assert g.subject == "grass.出一地一方"


def test_dangling_rule_ref_located():
    v = snapshot_ontology(spi.registry, "grass", "grass@danglerule")
    act = v.registry.actions[("grass", "出一地一方")]
    v.registry.actions[("grass", "出一地一方")] = replace(
        act, post_rules=act.post_rules + ("查无此规则",))
    rep = audit_gaps(v.registry, "grass")
    assert any(g.kind == "dangling_rule_ref" and "查无此规则" in g.detail for g in rep.blocking)


def test_dangling_write_and_link_endpoint():
    v = snapshot_ontology(spi.registry, "grass", "grass@dangle")
    act = v.registry.actions[("grass", "出一地一方")]
    v.registry.actions[("grass", "出一地一方")] = replace(act, writes=("查无此对象",))
    v.registry.links[("grass", "野关系")] = LinkType("野关系", "grass", "Site", "缺对象")
    rep = audit_gaps(v.registry, "grass")
    kinds = {g.kind for g in rep.blocking}
    assert {"dangling_write", "dangling_link_endpoint"} <= kinds


def test_report_summary():
    rep = audit_gaps(spi.registry, "grass")
    assert "grass" in rep.summary and "结构完整" in rep.summary
