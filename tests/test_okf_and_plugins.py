"""OKF 导出合规性 + 双本体（草业/辣椒）namespace 共存。"""
from __future__ import annotations

import yaml

from clife_onto_engine.okf import export_bundle
from clife_onto_engine.sdk import spi


def test_okf_bundle_conformance(tmp_path):
    bundle = export_bundle(spi.registry, "grass", str(tmp_path / "grass"))
    concepts = [p for p in bundle.rglob("*.md") if p.name not in ("index.md", "log.md")]
    assert concepts, "应导出概念文件"
    for md in concepts:
        text = md.read_text(encoding="utf-8")
        assert text.startswith("---"), f"{md} 缺 frontmatter"
        fm = yaml.safe_load(text.split("---", 2)[1])
        assert fm.get("type"), f"{md} 缺非空 type"        # OKF v0.1 唯一必填
    assert (bundle / "index.md").exists()


def test_rule_provenance_in_okf(tmp_path):
    bundle = export_bundle(spi.registry, "grass", str(tmp_path / "g"))
    txt = (bundle / "rules" / "乡土合规.md").read_text(encoding="utf-8")
    assert "# Citations" in txt and "GB/T" in txt          # 规则出处落地


def test_dual_ontology_isolation():
    grass_actions = {n for (ns, n) in spi.registry.actions if ns == "grass"}
    chili_actions = {n for (ns, n) in spi.registry.actions if ns == "chili"}
    assert "出一地一方" in grass_actions
    assert "制定种植方案" in chili_actions
    assert grass_actions.isdisjoint(chili_actions)        # namespace 隔离，互不串
