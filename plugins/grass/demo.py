"""端到端冒烟：用草业插件验证内核 Action 流水线。

跑三条路径：
  A. 合规 → commit（写即可见 + 审计快照 committed）
  B. 非乡土草种 → 写后 hard 违反 → 确定性回滚 + 结构化拒绝
  C. validate 预演 → 不落库，仅预测 would_commit

运行：  python -m plugins.grass.demo   （在仓库根目录）
"""
from __future__ import annotations

from clife_onto_engine import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi

from . import seed_reference_data  # 注册副作用：import 包即完成 SPI 注册


def main() -> None:
    store = InMemoryStore()
    seed_reference_data(store)
    engine = ActionEngine(spi.registry, store=store)
    contractor = Actor(id="u1", role="施工方")

    print("== A. 合规方案 → 期望 committed ==")
    a = engine.execute("grass", "出一地一方", {
        "site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300,
    }, contractor, schema_version="grass@0.1.0", ts="2026-06-28T13:00:00")
    print(f"  committed={a.committed} decision={getattr(a, 'decision', None)} "
          f"written={getattr(a, 'written', None)} hil={getattr(a, 'hil_required', None)}")
    print(f"  SeedPack 已落库可见: {store.get_object('SeedPack', 'sp_parcel_001')}")

    print("== B. 含非乡土草种(紫花苜蓿) → 期望 rejected + 回滚 ==")
    store_b = InMemoryStore(); seed_reference_data(store_b)
    engine_b = ActionEngine(spi.registry, store=store_b)
    b = engine_b.execute("grass", "出一地一方", {
        "site_id": "parcel_001", "species": ["碱茅", "紫花苜蓿"], "budget": 300,
    }, contractor, schema_version="grass@0.1.0", ts="2026-06-28T13:01:00")
    print(f"  committed={b.committed} phase={getattr(b, 'phase', None)}")
    for v in getattr(b, "violations", ()):  # 结构化拒绝，可喂 Agent 自动重试
        print(f"    ✗ {v.rule}: {v.message} | 建议: {v.suggestion}")
    print(f"  回滚验证 (不应落库): {store_b.get_object('SeedPack', 'sp_parcel_001')}")

    print("== C. validate 预演 → 不落库 ==")
    store_c = InMemoryStore(); seed_reference_data(store_c)
    engine_c = ActionEngine(spi.registry, store=store_c)
    p = engine_c.validate("grass", "出一地一方", {
        "site_id": "parcel_001", "species": ["碱茅"], "budget": 100,
    }, contractor)
    print(f"  would_commit={p.would_commit} staged={p.staged}")
    print(f"  预演无副作用 (不应落库): {store_c.get_object('SeedPack', 'sp_parcel_001')}")

    print("== D. 草易·快检评级：合格草样 → 期望 committed + 等级/溯源码 ==")
    store_d = InMemoryStore(); seed_reference_data(store_d)
    engine_d = ActionEngine(spi.registry, store=store_d)
    rancher = Actor(id="u2", role="养殖户")
    d = engine_d.execute("grass", "快检评级", {
        "batch_id": "B202606", "measurements": {"CP": 20, "NDF": 38, "ADF": 30, "RFV": 160, "霉菌毒素": 0.01},
    }, rancher, schema_version="grass@0.1.0", ts="2026-06-28T13:02:00")
    sample = store_d.get_object("ForageSample", "B202606") or {}
    print(f"  committed={d.committed} 等级={sample.get('grade')} 溯源码={sample.get('trace_code')} "
          f"effects={getattr(d, 'effects_scheduled', None)}")

    print("== E. 草易·快检评级：霉变超标 → 期望 rejected + 回滚 ==")
    store_e = InMemoryStore(); seed_reference_data(store_e)
    engine_e = ActionEngine(spi.registry, store=store_e)
    e = engine_e.execute("grass", "快检评级", {
        "batch_id": "B202607", "measurements": {"CP": 18, "NDF": 40, "ADF": 32, "RFV": 140, "霉菌毒素": 0.20},
    }, rancher, schema_version="grass@0.1.0", ts="2026-06-28T13:03:00")
    print(f"  committed={e.committed} phase={getattr(e, 'phase', None)}")
    for v in getattr(e, "violations", ()):
        print(f"    ✗ {v.rule}: {v.message} | 建议: {v.suggestion}")
    print(f"  回滚验证 (不应落库): {store_e.get_object('ForageSample', 'B202607')}")

    print(f"== 审计快照条数: A={len(engine.audit)} B={len(engine_b.audit)} "
          f"D={len(engine_d.audit)} E={len(engine_e.audit)} ==")
    for eng, tag in ((engine, "A·出一地一方"), (engine_d, "D·快检评级")):
        for snap in eng.audit.query("grass"):
            print(f"  audit[{tag}]: action={snap.action} decision={snap.decision} "
                  f"confidence={snap.confidence} evidence={len(snap.evidence)}条")


if __name__ == "__main__":
    main()
