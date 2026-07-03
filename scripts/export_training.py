"""导出三范式训练集（§4.4）—— 跑五闭环生成裁决轨迹 → 静态/路径/现象三范式 → JSONL。

对接 2026.12「高质量数据集」验收：把本体导成本体大模型的训练数据。
运行：python scripts/export_training.py  → build/training/grass/{static_structure,path_template,phenomenon_instance}.jsonl
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.trust.audit import AuditStore
from clife_onto_engine.training_export import export_training, write_training

import plugins.grass  # noqa: F401

# (动作, 参数, 角色) —— 五闭环各取合规+拒绝，产生多样裁决轨迹（现象级实例层）
RUNS = [
    ("出一地一方", {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300}, "施工方"),
    ("出一地一方", {"site_id": "parcel_001", "species": ["紫花苜蓿"], "budget": 300}, "施工方"),
    ("快检评级", {"batch_id": "b1", "measurements": {"CP": 20, "NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.0}}, "养殖户"),
    ("快检评级", {"batch_id": "b2", "measurements": {"CP": 20, "NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.2}}, "养殖户"),
    ("出碳汇核算报告", {"cp_id": "cp_001", "method_no": "CCER-GRASS-01"}, "碳汇开发"),
    ("出碳汇核算报告", {"cp_id": "cp_young", "method_no": "CCER-GRASS-01"}, "碳汇开发"),
    ("出杂交组合推荐", {"base_id": "G1", "candidate_id": "G2", "target_trait": "耐旱"}, "育种"),
    ("出作业参数", {"equipment_id": "E1", "operation": "播种", "params": {"播深": 4, "行距": 20}}, "机手"),
]


def main() -> int:
    store = InMemoryStore(); plugins.grass.seed_reference_data(store)
    audit = AuditStore()
    engine = ActionEngine(spi.registry, store=store, audit=audit)
    for action, params, role in RUNS:
        engine.execute("grass", action, params, Actor("u", role), schema_version="grass@0.1.0", ts="t")

    bundle = export_training(spi.registry, "grass", audits=audit.query("grass"))
    counts = write_training(bundle, ROOT / "build" / "training" / "grass")

    print("== 三范式训练集导出（grass）==")
    print(f"  静态结构层：{len(bundle['static']['objects'])} 对象 + {len(bundle['static']['links'])} 关系")
    print(f"  路径模板层：{len(bundle['paths']['paths'])} 条多跳路径模板")
    print(f"  现象级实例层：{len(bundle['phenomena']['traces'])} 条裁决轨迹（输入→规则→裁决→证据）")
    print(f"  → build/training/grass/ · 每文件条数：{counts}")
    # 示例：一条最长路径模板 + 一条拒绝轨迹
    longest = max(bundle["paths"]["paths"], key=lambda p: len(p["hops"]))
    print(f"\n  示例·路径模板：{longest['template']}")
    rej = next((t for t in bundle["phenomena"]["traces"] if t["decision"] == "rejected"), None)
    if rej:
        viol = [r["rule"] for r in rej["rules_evaluated"] if r["result"] == "violate"]
        print(f"  示例·现象轨迹：{rej['action']} → rejected · 违反 {viol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
