"""三范式训练集导出（§4.4）：静态结构 / 路径模板 / 现象级实例（审计轨迹）→ JSONL。"""
from __future__ import annotations

import json

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.trust.audit import AuditStore
from clife_onto_engine.training_export import (
    export_paths, export_phenomena, export_static, export_training, write_training,
)

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def test_static_structure_has_objects_and_links():
    st = export_static(spi.registry, "grass")
    assert st["paradigm"] == "static_structure"
    types = {o["type"] for o in st["objects"]}
    assert {"Site", "SeedPack", "GrassSpecies", "CarbonParcel"} <= types
    site = next(o for o in st["objects"] if o["type"] == "Site")
    assert site["primary_key"] == "parcel_id" and "region" in site["fields"]
    link_names = {l["link"] for l in st["links"]}
    assert {"suffers", "treated_by", "uses", "composed_of"} <= link_names


def test_path_templates_find_restoration_chain():
    paths = export_paths(spi.registry, "grass")["paths"]
    templates = {p["template"] for p in paths}
    assert any(t.startswith("Site →suffers→ Degradation →treated_by→ RestorationMethod →uses→ SeedPack")
               for t in templates)
    assert all(len(p["hops"]) >= 2 for p in paths)      # 至少 2 跳


def test_phenomena_from_audit_traces():
    audit = AuditStore()
    store = _seeded()
    eng = ActionEngine(spi.registry, store=store, audit=audit)
    # 一提交（合规配比）+ 一拒绝（非乡土），产生两条裁决轨迹
    eng.execute("grass", "出一地一方",
                {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                Actor("u", "施工方"), schema_version="v", ts="t")
    eng.execute("grass", "出一地一方",
                {"site_id": "parcel_001", "species": ["紫花苜蓿"], "budget": 300},
                Actor("u", "施工方"), schema_version="v", ts="t")
    ph = export_phenomena(spi.registry, "grass", audit.query("grass"))
    assert ph["paradigm"] == "phenomenon_instance" and len(ph["traces"]) == 2
    rejected = next(t for t in ph["traces"] if t["decision"] == "rejected")
    assert any(r["rule"] == "乡土合规" and r["result"] == "violate" for r in rejected["rules_evaluated"])


def test_write_training_emits_three_jsonl(tmp_path):
    bundle = export_training(spi.registry, "grass")
    counts = write_training(bundle, tmp_path)
    assert set(counts) == {"static_structure.jsonl", "path_template.jsonl", "phenomenon_instance.jsonl"}
    assert counts["static_structure.jsonl"] > 0 and counts["path_template.jsonl"] > 0
    # 每行是合法 JSON
    for line in (tmp_path / "path_template.jsonl").read_text(encoding="utf-8").splitlines():
        assert "template" in json.loads(line)
