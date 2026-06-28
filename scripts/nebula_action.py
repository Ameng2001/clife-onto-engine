"""集成验证：Action 引擎跑在真实 NebulaGraph 上。

证明：把内存后端换成 NebulaGraphStore，Action 流水线（guard→live-index→写后校验→
commit/回滚→审计）逐字不改即可运行；commit 真落图库、reject 对图库零写入。

前置：docker compose -f deploy/nebula/docker-compose.yml up -d  且 pip install nebula3-python
运行：python scripts/nebula_action.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.query.nebula_store import NebulaGraphStore
from clife_onto_engine.sdk import Actor, spi

from plugins.grass import seed_reference_data


def _seed_site(store, parcel: str) -> None:
    store.put_object("Site", parcel, {"parcel_id": parcel, "area_mu": 500,
                                       "region": "巴彦淖尔", "site_type": "盐碱"})


def main() -> None:
    store = NebulaGraphStore(ontology_id="grass", registry=spi.registry).connect()
    print("== bootstrap space=grass（建库建模，DDL 等待中…）==")
    store.bootstrap(drop=True)
    seed_reference_data(store)          # Site parcel_001 + 乡土名录 → 落 Nebula
    _seed_site(store, "parcel_002")     # reject 用例的地块

    engine = ActionEngine(spi.registry, store=store)   # ← 后端即 NebulaGraph
    contractor = Actor(id="u1", role="施工方")
    rancher = Actor(id="u2", role="养殖户")

    print("== A. 出一地一方·合规 → commit，真落 Nebula ==")
    a = engine.execute("grass", "出一地一方",
                       {"site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300},
                       contractor, schema_version="grass@0.1.0", ts="2026-06-28T14:00:00")
    print(f"  committed={a.committed} written={a.written}")
    print(f"  读回 Nebula SeedPack: {store.get_object('SeedPack', 'sp_parcel_001')}")
    print(f"  读回 Nebula Project : {store.get_object('Project', 'proj_parcel_001')}")

    print("== B. 出一地一方·非乡土草种 → 回滚，Nebula 零写入 ==")
    b = engine.execute("grass", "出一地一方",
                       {"site_id": "parcel_002", "species": ["碱茅", "紫花苜蓿"], "budget": 300},
                       contractor, schema_version="grass@0.1.0", ts="2026-06-28T14:01:00")
    print(f"  committed={b.committed} 违反={[v.rule for v in getattr(b, 'violations', ())]}")
    print(f"  读回 Nebula SeedPack(应 None): {store.get_object('SeedPack', 'sp_parcel_002')}")

    print("== D. 快检评级·合格 → commit，等级落 Nebula ==")
    d = engine.execute("grass", "快检评级",
                       {"batch_id": "B202606", "measurements": {"CP": 20, "NDF": 38, "ADF": 30, "RFV": 160, "霉菌毒素": 0.01}},
                       rancher, schema_version="grass@0.1.0", ts="2026-06-28T14:02:00")
    sample = store.get_object("ForageSample", "B202606") or {}
    print(f"  committed={d.committed} 读回 Nebula 等级={sample.get('grade')} 溯源码={sample.get('trace_code')}")

    print("== E. 快检评级·霉变 → 回滚，Nebula 零写入 ==")
    e = engine.execute("grass", "快检评级",
                       {"batch_id": "B202607", "measurements": {"CP": 18, "NDF": 40, "ADF": 32, "RFV": 140, "霉菌毒素": 0.20}},
                       rancher, schema_version="grass@0.1.0", ts="2026-06-28T14:03:00")
    print(f"  committed={e.committed} 违反={[v.rule for v in getattr(e, 'violations', ())]}")
    print(f"  读回 Nebula ForageSample(应 None): {store.get_object('ForageSample', 'B202607')}")

    ok = (a.committed and not b.committed and d.committed and not e.committed
          and store.get_object("SeedPack", "sp_parcel_002") is None
          and store.get_object("ForageSample", "B202607") is None
          and (store.get_object("ForageSample", "B202606") or {}).get("grade") == "特级")
    store.close()
    print(f"== {'OK：Action 流水线在真实 NebulaGraph 上 commit/回滚均正确' if ok else '失败：断言不符'} ==")


if __name__ == "__main__":
    main()
