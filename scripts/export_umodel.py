"""把本体导出为 UModel model pack（可被 umodel-server 装载、Explorer 浏览、SPL 查）。

运行：  python scripts/export_umodel.py   → 输出到 build/umodel/<ontology>/

UModel = 引擎之上的只读语义层；本脚本只导**可读半区**（对象/关系/物理映射/运行时实例），
治理写半区（Rule/Action）不映射（见 clife_onto_engine/umodel.py 与 docs/04-umodel-interop.md）。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.umodel import export_pack

import plugins.grass  # noqa: F401  (import 即完成 SPI 注册)
import plugins.chili  # noqa: F401

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _seed_grass() -> InMemoryStore:
    """构造一个含实例 + 拓扑的运行时 store，让导出的 pack 在 Explorer 里有图可看。

    实例数据来自插件的参考数据接口 + 少量演示拓扑（真实落地走 tenants 映射注入）。
    """
    store = InMemoryStore()
    plugins.grass.seed_reference_data(store)  # Site/parcel_001 + NativeListing
    # 演示拓扑：退化 → 修复方法（让 .topo 多跳有东西可走）
    store.put_object("Degradation", "deg_001", {"deg_id": "deg_001", "level": "重度", "type": "盐碱化"})
    store.put_object("RestorationMethod", "m_pen", {"method_id": "m_pen", "name": "喷播"})
    store.put_object("RestorationMethod", "m_sup", {"method_id": "m_sup", "name": "补播"})
    from clife_onto_engine.query import StagedLink
    store.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg_001"))
    store.put_link(StagedLink("treated_by", "Degradation", "deg_001", "RestorationMethod", "m_pen"))
    store.put_link(StagedLink("treated_by", "Degradation", "deg_001", "RestorationMethod", "m_sup"))
    return store


def _seed_chili() -> InMemoryStore:
    """chili 运行时 store —— 验证「换行业零改」延伸到读层。

    chili 插件未声明任何 LinkType（不建模关系），故读层是对象 + 实例可浏览、拓扑为空——
    这恰是 chili 建模的诚实反映：同一导出器、同一 UModel，只换领域词、零内核/导出器改动。
    """
    store = InMemoryStore()
    plugins.chili.seed_reference_data(store)  # Field/field_001 + 海南适配品种名录
    # 多对象类实例，让 .entity 跨类型有内容可看（无关系，因 chili 未声明 Link）
    store.put_object("Field", "field_002", {"field_id": "field_002", "area_mu": 50,
                                            "region": "云南", "soil_type": "红壤"})
    store.put_object("PlantingPlan", "plan_field_001",
                     {"field_id": "field_001", "variety": "朝天椒", "density": 2200})
    store.put_object("GradeSample", "g_001", {"batch_id": "g_001"})
    return store


def main() -> None:
    seeds = {"grass": _seed_grass(), "chili": _seed_chili()}
    for ns, store in seeds.items():
        out = ROOT / "build" / "umodel" / ns
        pack = export_pack(spi.registry, ns, str(out), store=store, timestamp="2026-06-28")
        ent = pack / "sample-data" / "entities.json"
        rel = pack / "sample-data" / "relations.json"
        import json
        n_es = len(list((pack / "umodel" / ns / "entity_set").glob("*.yaml")))
        link_dir = pack / "umodel" / ns / "link" / "entity_set_link"
        n_lk = len(list(link_dir.glob("*.yaml"))) if link_dir.exists() else 0
        sto_dir = pack / "umodel" / ns / "storage"
        n_st = len(list(sto_dir.glob("*.yaml"))) if sto_dir.exists() else 0
        n_e = len(json.loads(ent.read_text(encoding="utf-8")))
        n_r = len(json.loads(rel.read_text(encoding="utf-8")))
        print(f"== {ns}: {n_es} entity_set · {n_lk} link · {n_st} storage "
              f"· {n_e} 实例 · {n_r} 关系 → {pack.relative_to(ROOT)} ==")


if __name__ == "__main__":
    main()
