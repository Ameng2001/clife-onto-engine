"""plugin.yaml 清单 + 槽位 5（术语表）/ 6（复核角色）：声明式加载 + 术语表进 LLM 能力清单。"""
from __future__ import annotations

from clife_onto_engine.intent.manifest import build_manifest, render_manifest
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.registry import SPI

import plugins.grass  # noqa: F401 —— import 时已 load_manifest(plugin.yaml)


def test_grass_manifest_loaded_glossary_and_agents():
    # 槽位5：术语表（含把安全字段别名 mycotoxin 映射到规范键 霉菌毒素）
    myco = spi.registry.glossary[("grass", "霉菌毒素")]
    assert "mycotoxin" in myco["aliases"] and "aflatoxin" in myco["aliases"]
    # 槽位6：复核角色（HIL）声明式化
    assert spi.registry.agents[("grass", "碳汇核证员")]["reviews"] == ["出碳汇核算报告"]
    assert spi.registry.agents[("grass", "乡土草种合规官")]["reviews"] == ["出一地一方"]


def test_glossary_rendered_into_intent_manifest():
    text = render_manifest(build_manifest(spi.registry, "grass"))
    assert "术语表" in text
    assert "霉菌毒素" in text and "mycotoxin" in text          # 规范用词 + 别名都进了 LLM 提示
    assert "相对饲用价值" in text                              # 定义也进了


def test_load_manifest_with_schema_and_slots(tmp_path):
    (tmp_path / "schema.yaml").write_text(
        "objects:\n  - {name: Foo, primary_key: fid}\n", encoding="utf-8")
    (tmp_path / "plugin.yaml").write_text(
        "plugin: demo\nontology: demo\nschema: schema.yaml\n"
        "glossary:\n  - {term: T, aliases: [t1], definition: d}\n"
        "agents:\n  - {role: R, reviews: [A]}\n", encoding="utf-8")
    s = SPI()  # 独立 registry
    stats = s.load_manifest(tmp_path / "plugin.yaml")
    assert stats == {"ontology": "demo", "objects": 1, "links": 0, "glossary": 1, "agents": 1}
    assert ("demo", "Foo") in s.registry.objects                # schema 也经清单加载
    assert s.registry.glossary[("demo", "T")]["aliases"] == ["t1"]
    assert s.registry.agents[("demo", "R")]["reviews"] == ["A"]
