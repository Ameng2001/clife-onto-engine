"""服务边界身份解析 smoke（生产化·多租户）—— 凭据认证成 Principal，驱动 tenant/actor。全离线。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.identity import Principal, StaticIdentityResolver


def main() -> int:
    fails = 0
    r = (StaticIdentityResolver()
         .add("key-shigongfang", "tenantA", "u1", "施工方")
         .add("key-guest", "tenantA", "g1", "游客"))

    p = r.resolve("key-shigongfang")
    ok = p == Principal("tenantA", "u1", "施工方") and p.actor.role == "施工方"
    print(f"== 合法凭据→Principal（认证身份）：{'✓' if ok else '✗'} · {p} ==")
    fails += not ok

    ok2 = r.resolve("bad-key") is None
    print(f"== 非法凭据→None（将触发 401）：{'✓' if ok2 else '✗'} ==")
    fails += not ok2

    # 认证角色不同 → 授权/角色判定用认证出来的 role
    guest = r.resolve("key-guest")
    ok3 = guest.role == "游客" and guest.tenant == "tenantA"
    print(f"== 认证角色驱动（游客）：{'✓' if ok3 else '✗'} ==")
    fails += not ok3

    if fails:
        print(f"\n✗ 身份解析 smoke 失败（{fails}）"); return 1
    print("\n✓ 服务边界身份解析 smoke 全通过：凭据→认证身份 · 非法→401 · 身份驱动 tenant/role")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
