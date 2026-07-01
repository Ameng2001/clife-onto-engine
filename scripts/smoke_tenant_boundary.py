"""租户→本体访问边界 smoke（生产化·多租户）—— 跨租户/跨本体在边界即拒。全离线。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.authz import TenantAccessPolicy


def main() -> int:
    fails = 0
    # 策略：tenantA 只授权 grass；tenantB 授权 chili
    p = TenantAccessPolicy(default_allow=False).grant("tenantA", "grass").grant("tenantB", "chili")

    checks = [
        ("tenantA→grass 通",       p.allows("tenantA", "grass"),  True),
        ("tenantA→chili 拒",       p.allows("tenantA", "chili"),  False),
        ("tenantB→grass 拒",       p.allows("tenantB", "grass"),  False),
        ("未知租户→grass 拒",       p.allows("tenantX", "grass"),  False),
    ]
    for name, got, want in checks:
        ok = got == want
        print(f"== {name}：{'✓' if ok else '✗'} ==")
        fails += not ok

    # default_allow=True 时未声明租户放行（宽松部署）
    p2 = TenantAccessPolicy(default_allow=True)
    ok2 = p2.allows("anyone", "grass")
    print(f"== default_allow 宽松放行：{'✓' if ok2 else '✗'} ==")
    fails += not ok2

    if fails:
        print(f"\n✗ 租户边界 smoke 失败（{fails}）"); return 1
    print("\n✓ 租户→本体访问边界 smoke 全通过：跨租户/跨本体拒 · 授权通 · default 可配")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
