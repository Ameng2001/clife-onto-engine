"""声明式授权 smoke（生产化·多租户）——谁能做什么，引擎前置强制。全离线。

grass 注入授权策略：只授权"施工方"出方案。游客越权 → unauthorized（无任何写、审计留痕）；
施工方 → 正常 commit。授权在 guard/执行之前，越权不产生副作用。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.authz import AuthzPolicy
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def main() -> int:
    fails = 0
    policy = AuthzPolicy(default_allow=False).grant("grass", "出一地一方", "施工方")

    # 1) 游客越权 → unauthorized，无任何写，审计留痕
    store = _seeded()
    eng = ActionEngine(spi.registry, store=store, authz=policy)
    res = eng.execute("grass", "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                      Actor("guest", "游客"), schema_version="grass@0.1.0")
    wrote = store.get_object("Project", "proj_parcel_001") is not None
    au = eng.audit.query("grass")[-1]
    ok = (not res.committed) and getattr(res, "phase", "") == "authz" and (not wrote) \
        and au.decision == "unauthorized"
    print(f"== 游客越权→unauthorized（无写+审计）：{'✓' if ok else '✗'} · phase={getattr(res,'phase','')} · 审计={au.decision} ==")
    fails += not ok

    # 2) 施工方被授权 → 正常 commit
    store2 = _seeded()
    eng2 = ActionEngine(spi.registry, store=store2, authz=policy)
    res2 = eng2.execute("grass", "出一地一方",
                        {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                        Actor("u1", "施工方"), schema_version="grass@0.1.0")
    ok2 = res2.committed
    print(f"== 施工方授权→commit：{'✓' if ok2 else '✗'} ==")
    fails += not ok2

    # 3) 无 authz → 向后兼容（游客也能跑到业务 guard，被「角色权限」拦而非 authz）
    eng3 = ActionEngine(spi.registry, store=_seeded())  # 无 authz
    res3 = eng3.execute("grass", "出一地一方",
                        {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
                        Actor("g", "游客"), schema_version="grass@0.1.0")
    ok3 = (not res3.committed) and getattr(res3, "phase", "") == "guard"  # 业务 guard「角色权限」拦
    print(f"== 无 authz 向后兼容（走业务 guard）：{'✓' if ok3 else '✗'} · phase={getattr(res3,'phase','')} ==")
    fails += not ok3

    if fails:
        print(f"\n✗ 授权 smoke 失败（{fails}）"); return 1
    print("\n✓ 声明式授权 smoke 全通过：越权前置拒绝无副作用 · 授权正常 · 无 authz 兼容")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
