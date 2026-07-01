"""本体治理缺口审计 smoke（C1 运行时侧）——上线前静态查"还没填完/治理缺口"。

grass 结构完整（无 blocking），列出 advisory（无出处的 declarative guard）；
构造残缺版本（去 handler / 悬空规则引用 / 悬空关系端点）→ blocking 精确定位。全离线。
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.gaps import audit_gaps
from clife_onto_engine.metamodel import ActionDef, LinkType
from clife_onto_engine.sdk import spi
from clife_onto_engine.versioning import snapshot_ontology

import plugins.grass  # noqa: F401


def main() -> int:
    fails = 0
    # 1) grass 结构完整：无 blocking
    rep = audit_gaps(spi.registry, "grass")
    print("==", rep.summary, "==")
    for g in rep.advisory:
        print(f"   · advisory {g.kind} · {g.subject} · {g.detail}")
    ok = rep.ok
    print(f"== grass 无结构缺口：{'✓' if ok else '✗ ' + str(rep.blocking)} ==")
    fails += not ok

    # 2) 残缺版本：去 handler + 悬空规则引用 + 悬空关系端点
    v = snapshot_ontology(spi.registry, "grass", "grass@broken")
    act = v.registry.actions[("grass", "出一地一方")]
    v.registry.actions[("grass", "出一地一方")] = replace(
        act, impl=None, post_rules=act.post_rules + ("不存在的规则",))
    v.registry.links[("grass", "野关系")] = LinkType("野关系", "grass", "Site", "不存在的对象")

    rep2 = audit_gaps(v.registry, "grass")
    kinds = {g.kind for g in rep2.blocking}
    ok2 = (not rep2.ok) and {"action_no_handler", "dangling_rule_ref",
                             "dangling_link_endpoint"} <= kinds
    print(f"== 残缺版本 blocking 定位：{'✓' if ok2 else '✗'} · {sorted(kinds)} ==")
    for g in rep2.blocking:
        print(f"   ✗ blocking {g.kind} · {g.subject} · {g.detail}")
    fails += not ok2

    if fails:
        print(f"\n✗ 缺口审计 smoke 失败（{fails}）"); return 1
    print("\n✓ 本体治理缺口审计 smoke 全通过：结构完整可判 · 残缺缺口精确定位")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
