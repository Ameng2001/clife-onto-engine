"""UModel pack 导出：结构保真 + 治理写半区不外泄 + 离线 schema 校验。"""
from __future__ import annotations

import pathlib

import yaml

from clife_onto_engine.query import InMemoryStore, StagedLink
from clife_onto_engine.sdk import spi
from clife_onto_engine.umodel import export_pack, _eid

import plugins.grass  # noqa: F401  (SPI 注册)

SCHEMA_DIR = (pathlib.Path(__file__).resolve().parent.parent
              / "third-party" / "umodel-schemas" / "schemas")


def _pack(tmp_path, store=None):
    return export_pack(spi.registry, "grass", str(tmp_path / "grass"), store=store)


def test_objects_and_links_emitted(tmp_path):
    pack = _pack(tmp_path)
    es = {p.stem for p in (pack / "umodel" / "grass" / "entity_set").glob("*.yaml")}
    assert {"Site", "Degradation", "RestorationMethod"} <= es
    site = yaml.safe_load(
        (pack / "umodel" / "grass" / "entity_set" / "Site.yaml").read_text("utf-8"))
    assert site["kind"] == "entity_set"
    assert site["metadata"]["name"] == "grass.Site"
    # 主键必是一个存在的 field（properties 里没有 parcel_id 时由导出器补齐）
    field_names = {f["name"] for f in site["spec"]["fields"]}
    assert site["spec"]["primary_key_fields"][0] in field_names
    link = yaml.safe_load(
        (pack / "umodel" / "grass" / "link" / "entity_set_link" / "suffers.yaml").read_text("utf-8"))
    assert link["spec"]["entity_link_type"] == "suffers"
    assert link["spec"]["src"]["name"] == "grass.Site"


def test_governed_write_elements_not_mapped(tmp_path):
    """Function/Rule/Action（治理写半区）不得出现在 pack —— UModel 是只读层。"""
    pack = _pack(tmp_path)
    kinds = {yaml.safe_load(p.read_text("utf-8")).get("kind")
             for p in (pack / "umodel").rglob("*.yaml")}
    # 只应有只读建模 kind，绝无任何"可执行/规则/动作"语义的 kind
    assert kinds <= {"entity_set", "entity_set_link", "external_storage"}


def test_runtime_instances_deterministic(tmp_path):
    store = InMemoryStore()
    plugins.grass.seed_reference_data(store)
    store.put_object("Degradation", "deg_001", {"deg_id": "deg_001", "level": "重度"})
    store.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg_001"))
    import json
    p1 = _pack(tmp_path / "a", store)
    p2 = _pack(tmp_path / "b", store)
    e1 = (p1 / "sample-data" / "entities.json").read_text("utf-8")
    e2 = (p2 / "sample-data" / "entities.json").read_text("utf-8")
    assert e1 == e2, "导出须确定性可重放"
    rels = json.loads((p1 / "sample-data" / "relations.json").read_text("utf-8"))
    # __entity_id__ 是 (domain,type,key) 的确定性 32-hex（UModel 格式要求）；关系两端引用须一致
    assert any(r["__relation_type__"] == "suffers"
               and r["__src_entity_id__"] == _eid("grass", "Site", "parcel_001") for r in rels)
    ents = json.loads((p1 / "sample-data" / "entities.json").read_text("utf-8"))
    for e in ents:                                        # 全部实例 ID 合 UModel 32-hex 约定
        eid = e["__entity_id__"]
        assert len(eid) == 32 and all(c in "0123456789abcdef" for c in eid)


def test_offline_schema_validation(tmp_path):
    """对 vendored schema 做离线必填校验：正例过、抹掉 metadata.name 被拦。"""
    from scripts.smoke_umodel import _load_schemas, validate_pack
    kinds, includes = _load_schemas()
    pack = _pack(tmp_path)
    assert validate_pack(pack, kinds, includes) == []
    victim = next((pack / "umodel" / "grass" / "entity_set").glob("*.yaml"))
    doc = yaml.safe_load(victim.read_text("utf-8"))
    doc["metadata"].pop("name")
    victim.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), "utf-8")
    errs = validate_pack(pack, kinds, includes)
    assert any("缺必填 'name'" in e for e in errs)
