"""CQ 验收回路 smoke（C3）—— 闭合建模→运行时环。

grass CQ 套件对**当前版本**全通过；对**故意去掉「乡土合规」的版本**，依赖它的 CQ 失败
（能力回归被验收门抓住）。全离线、无 LLM。
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.cq import run_cq_suite
from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.versioning import snapshot_ontology

import plugins.grass  # noqa: F401
from plugins.grass.cq import CQ_SUITE


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def main() -> int:
    fails = 0
    # 1) 当前版本：CQ 套件应全通过
    rep = run_cq_suite(CQ_SUITE, spi.registry, store=_seeded())
    print("==", rep.summary, "==")
    for r in rep.results:
        print(f"   {'✓' if r.passed else '✗'} {r.name}（{r.kind}）· 期望 {r.expected} · 实际 {r.actual}")
    ok = rep.ok
    print(f"== 当前版本全通过：{'✓' if ok else '✗'} ==")
    fails += not ok

    # 2) 去掉「乡土合规」的版本：依赖它的 CQ 应失败（回归被抓）
    v = snapshot_ontology(spi.registry, "grass", "grass@no-native")
    # 把「出一地一方」的 post_rules 去掉「乡土合规」
    act = v.registry.actions[("grass", "出一地一方")]
    v.registry.actions[("grass", "出一地一方")] = replace(
        act, post_rules=tuple(r for r in act.post_rules if r != "乡土合规"))

    rep2 = run_cq_suite(CQ_SUITE, v.registry, store=_seeded())
    # 「非乡土草种被拦」这条应从 pass 变 fail（规则被删，非乡土草种现在会 commit）
    native_cq = next(r for r in rep2.results if r.name == "非乡土草种被拦")
    ok2 = (not native_cq.passed) and (not rep2.ok)
    print(f"== 去规则版本抓到回归（非乡土草种被拦 → 失败）：{'✓' if ok2 else '✗'} · {native_cq.detail} ==")
    fails += not ok2

    if fails:
        print(f"\n✗ CQ 验收 smoke 失败（{fails}）"); return 1
    print("\n✓ CQ 验收回路 smoke 全通过：当前版本全 pass · 版本削弱规则被验收门抓住")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
