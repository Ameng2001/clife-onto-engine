"""附着知识：声明/加载/检索、四类标准化、按 kind 过滤、无绑定空、Explorer 呈现。"""
from __future__ import annotations

from clife_onto_engine.knowledge import knowledge_for, knowledge_of_kind
from clife_onto_engine.query import InMemoryStore, StagedLink
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401


def test_object_carries_knowledge():
    ks = knowledge_for(spi.registry, "grass", "Degradation")
    assert {k.kind for k in ks} == {"diagnostic", "playbook"}
    assert all(k.object_type == "Degradation" and k.content for k in ks)


def test_standard_kinds_covered():
    kinds = set()
    for ot in ("Site", "Degradation", "RestorationMethod"):
        kinds |= {k.kind for k in knowledge_for(spi.registry, "grass", ot)}
    assert {"template", "diagnostic", "playbook", "reference"} <= kinds


def test_filter_by_kind():
    tpl = knowledge_of_kind(spi.registry, "grass", "Site", "template")
    assert len(tpl) == 1 and tpl[0].kind == "template"


def test_no_binding_empty_and_coexists_with_rule():
    assert knowledge_for(spi.registry, "grass", "NativeListing") == ()
    assert ("grass", "乡土合规") in spi.registry.rules      # 强制知识仍是 Rule


def test_refs_carried():
    ks = knowledge_for(spi.registry, "grass", "Degradation")
    assert any(k.refs for k in ks)                          # 出处/引用带上


def test_explorer_surfaces_knowledge():
    from clife_onto_engine.explorer import render
    s = InMemoryStore(); plugins.grass.seed_reference_data(s)
    s.put_object("Degradation", "d1", {"deg_id": "d1", "level": "重度"})
    h = render(spi.registry, s, "grass", cytoscape_js="/*x*/")
    assert '"knowledge"' in h and "盐碱化常见成因" in h and "附着知识" in h
