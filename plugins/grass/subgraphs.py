"""Phase 1 · 6 大子图 schema 层贯通 —— 声明育种/碳汇/监测等子图的对象与关系。

**只声明 schema**（对象 + 关系 + 代表属性），不含 data/rule/action——后者随各子图
Action 闭环上线时增量补（Phase 1 只上线草修/草易两个闭环，其余子图先贯通骨架）。

对齐方案第五章：§5.4 实体类型、§5.5 关系类型、§5.6 六大子图。
子图 2（生态修复）/3（饲草品质）的核心已在 __init__.py / forage.py，此处补齐其余对象
与全部 6 子图的导航关系，使本体骨架完整、可 OQL/Search Around 导航、可供 OKF 导出。
"""
from __future__ import annotations

from clife_onto_engine.sdk import EdgeSemantics, LinkType, ObjectType, PropertySpec, spi

from . import ONTOLOGY

_H, _D = EdgeSemantics.HYPOTHESIS, EdgeSemantics.DERIVATION


def _obj(name: str, pk: str, props=()) -> None:
    spi.registry.add_object(ObjectType(name=name, namespace=ONTOLOGY, primary_key=pk, properties=props))


def _link(name: str, src: str, tgt: str, sem: EdgeSemantics = _D) -> None:
    spi.registry.add_link(LinkType(name, ONTOLOGY, src, tgt, edge_semantics=sem))


def _P(n, t, **kw):
    return PropertySpec(n, t, **kw)


# ── 子图 1 · 草种-立地-适配（扩展：立地/区域/性状/气象对象 + 导航关系）──────────
_obj("SiteType", "name", (_P("features", "string"),))                         # §5.4 #7
_obj("Region", "region_code", (_P("climate", "string"), _P("sow_window", "string")))  # #25
_obj("Trait", "name", (_P("unit", "string"),))                                # #4（育种共用）
_obj("Weather", "obs_id", (_P("rainfall", "number"), _P("temp", "number")))    # #20
_link("adapts_to", "GrassSpecies", "SiteType")   # 导航/未来边数据；运行时「立地适配」暂读 GrassSpecies.adapts_to 属性
_link("has_trait", "GrassSpecies", "Trait")
_link("suitable_for", "GrassSpecies", "Region")
_link("constrained_by", "RestorationMethod", "Weather", _H)   # 施工窗口（§5.5 #27）
_link("has_site_type", "Site", "SiteType")                    # §5.5 #9

# ── 子图 2 · 生态修复（扩展：材料对象 + 剩余关系）──────────────────────────────
_obj("Material", "material_id", (_P("kind", "string"), _P("dosage", "number")))  # §5.4 #11
_link("contains_material", "SeedPack", "Material")   # §5.5 #14
_link("applied_in", "RestorationMethod", "Project")  # #15
_link("achieves", "Project", "QualityIndex")         # #16（逐年成效）

# ── 子图 3 · 饲草品质（扩展：饲草/畜群/日粮 + 关系）───────────────────────────
_obj("Forage", "forage_id", (_P("type", "string"),))                          # §5.4 #12
_obj("Livestock", "herd_id", (_P("species", "string"), _P("count", "number")))  # #14
_obj("Ration", "ration_id", (_P("cost", "number"),))                          # #15
_link("feeds", "Forage", "Livestock")     # §5.5 #20
_link("has_ration", "Livestock", "Ration")  # #21

# ── 子图 4 · 育种（种质/品种/基因标记 + 关系）────────────────────────────────
_obj("Germplasm", "germplasm_id", (_P("species", "string"), _P("germination", "number")))  # §5.4 #3
_obj("Variety", "variety_id", (_P("name", "string"), _P("cert_no", "string")))  # #2
_obj("GeneMarker", "marker_id", (_P("effect", "number"),))                     # #5
_link("carries_marker", "Germplasm", "GeneMarker")  # §5.5 #7
_link("marks", "GeneMarker", "Trait")               # #6（GWAS）
_link("crossed_to", "Germplasm", "Germplasm", _H)   # #5（杂交亲本）
_link("derived_from", "Variety", "Germplasm")       # #4
_link("certified_by", "Variety", "Standard")        # #23（品种审定）

# ── 子图 5 · 碳汇-生态价值 —— 已升级为**活闭环**，对象/关系/规则/Action 见 carbon.py ──

# ── 子图 6 · 草原监测-灾害（观测/灾害/鼠虫害 + 关系）─────────────────────────
_obj("MonitorObs", "obs_key", (_P("coverage", "number"), _P("biomass", "number")))  # §4.8 监测观测
_obj("Hazard", "hazard_id", (_P("kind", "string"), _P("threshold", "number")))  # §5.4 #21
_obj("Pest", "pest_id", (_P("kind", "string"), _P("threshold", "number")))     # #22
_link("threatened_by", "Site", "Hazard", _H)  # §5.5 #25
_link("controlled_by", "Pest", "Material")    # #26（生态防控）


# ── 6 子图 manifest（贯通性自检用；对齐 §5.6）───────────────────────────────
SUBGRAPHS = {
    "1 草种-立地-适配": {"objects": ("GrassSpecies", "SiteType", "Trait", "Region", "Weather"),
                    "links": ("adapts_to", "has_trait", "suitable_for", "constrained_by")},
    "2 生态修复": {"objects": ("Site", "Degradation", "RestorationMethod", "SeedPack", "Material", "Project", "QualityIndex"),
               "links": ("suffers", "treated_by", "uses", "composed_of", "contains_material", "applied_in", "achieves")},
    "3 饲草品质": {"objects": ("Forage", "ForageSample", "QualityIndex", "Standard", "Livestock", "Ration"),
               "links": ("has_quality", "measured_by", "feeds", "has_ration")},
    "4 育种": {"objects": ("Germplasm", "Variety", "Trait", "GeneMarker"),
             "links": ("carries_marker", "marks", "crossed_to", "derived_from", "certified_by")},
    "5 碳汇-生态价值": {"objects": ("CarbonParcel", "Methodology", "Site", "RestorationMethod", "Standard"),
                  "links": ("sequesters", "has_site_type", "measured_by")},
    "6 草原监测-灾害": {"objects": ("Site", "MonitorObs", "Hazard", "Pest", "Weather", "Degradation"),
                  "links": ("threatened_by", "suffers", "constrained_by", "controlled_by")},
}
