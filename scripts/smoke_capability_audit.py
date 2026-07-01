"""Capability 越界运行时审计 smoke（A 弧·安全可观测）—— 越界不崩、回滚、留痕、结构化拒绝。全离线。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


def _breach(ctx):
    ctx.stage_write("SeedPack", "x", {})   # SeedPack 未在 writes 声明 → 沙箱拦


def main() -> int:
    fails = 0
    spi.registry.actions[("grass", "_breach")] = ActionDef(
        name="_breach", namespace="grass", writes=(), validate_supported=True, impl=_breach)
    try:
        store = InMemoryStore()
        eng = ActionEngine(spi.registry, store=store)
        res = eng.execute("grass", "_breach", {}, Actor("attacker", "施工方"), schema_version="v")
        au = eng.audit.query("grass")[-1]
        wrote = store.get_object("SeedPack", "x") is not None
        ok = (not res.committed) and getattr(res, "phase", "") == "capability" \
            and (not wrote) and au.decision == "capability_violation"
        print(f"== 越界→回滚+审计+结构化拒绝（不崩）：{'✓' if ok else '✗'} · "
              f"phase={getattr(res,'phase','')} · 审计={au.decision} · 有残留写={wrote} ==")
        fails += not ok

        # validate 也捕获
        prev = eng.validate("grass", "_breach", {}, Actor("a", "施工方"))
        ok2 = (not prev.would_commit) and any(v.rule == "capability" for v in prev.violations)
        print(f"== 预演捕获越界：{'✓' if ok2 else '✗'} ==")
        fails += not ok2
    finally:
        del spi.registry.actions[("grass", "_breach")]

    if fails:
        print(f"\n✗ Capability 越界审计 smoke 失败（{fails}）"); return 1
    print("\n✓ Capability 越界运行时审计 smoke 全通过：越界不崩 · 确定性回滚 · 安全留痕 · 结构化拒绝")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
