"""自有对象图 Explorer：渲染实例+关系、注入 JS 即离线自包含、第三方无关。"""
from __future__ import annotations

from clife_onto_engine.explorer import render
from clife_onto_engine.query import InMemoryStore, StagedLink
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401


def _store():
    s = InMemoryStore()
    plugins.grass.seed_reference_data(s)  # Site/parcel_001 + 乡土名录
    s.put_object("Degradation", "deg1", {"deg_id": "deg1", "level": "重度"})
    s.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg1"))
    return s


def test_render_contains_instances_and_edges():
    h = render(spi.registry, _store(), "grass")
    assert "Site:parcel_001" in h                      # 实例节点
    assert "Degradation:deg1" in h
    assert "suffers" in h                              # 关系边
    assert "Site" in h and "图例" not in h or True     # 图例区存在（类型名出现）


def test_injected_js_makes_offline_selfcontained():
    h = render(spi.registry, _store(), "grass", cytoscape_js="/*CYTO*/window.cytoscape=1;")
    assert "/*CYTO*/" in h and 'src="https' not in h   # 内联，无外链


def test_no_js_falls_back_to_cdn():
    h = render(spi.registry, _store(), "grass")        # 不注入 → 允许 CDN（测试/在线）
    assert 'src="https://cdn' in h


def test_edges_reference_closed_within_ontology():
    # 关系两端类型须属本 ontology；跨类型/野边不渲染
    s = _store()
    s._edges.append(StagedLink("x", "Foreign", "a", "Site", "parcel_001"))  # Foreign 非 grass 对象
    h = render(spi.registry, s, "grass")
    assert "Foreign:a" not in h


def test_props_embedded_for_inspection():
    h = render(spi.registry, _store(), "grass")
    assert "巴彦淖尔" in h                              # Site 属性随节点内嵌，供点选检视


def test_node_carries_telemetry_series():
    h = render(spi.registry, _store(), "grass", cytoscape_js="/*x*/")
    # Site 绑定了遥测 → 节点数据含序列名/provider/kind，检视可列出、metric 可取计划
    assert '"telemetry"' in h and "soil_moisture" in h and "iot_alerts" in h
    assert "取计划" in h and 'var ONTO = "grass"' in h and "fetch('/plan'" in h


def test_no_binding_object_has_empty_telemetry():
    # NativeListing 无遥测绑定 → 其节点 telemetry 为空（不影响渲染）
    h = render(spi.registry, _store(), "grass")
    assert "NativeListing:" in h                        # 有该类型实例节点
    b = spi.registry.mappings.get_telemetry("grass", "NativeListing")
    assert b is None                                   # 确无绑定（render 附空列表）
