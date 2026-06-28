"""冒烟：SPI 沙箱 —— Capability 的四层运行时约束都真的拦得住。

用一个隔离的本体（iso，中性类型 A/B）直接驱动 Capability，证明：
  1. 租户/类型作用域：访问未声明类型被拒
  2. 写声明强制：stage_write 未在 Action.writes 里声明的类型被拒
  3. Function 最小权限：Function 读取 reads 之外的类型被拒
  4. 能力收窄：内核内部（view/changeset/base store）在门面上不可达

运行：  python scripts/smoke_sandbox.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryGraphStore, QueryView
from clife_onto_engine.sdk import Capability, CapabilityError, ObjectType, Registry, SPI
from clife_onto_engine.sdk.context import ActionContext, Actor


def _expect_block(label: str, fn) -> None:
    try:
        fn()
        print(f"  ✗ 未拦截：{label}")
    except CapabilityError as e:
        print(f"  ✓ 拦截 {label}: {e}")


def main() -> None:
    iso = SPI(Registry())
    reg = iso.registry
    reg.add_object(ObjectType("A", "iso", "ak"))
    reg.add_object(ObjectType("B", "iso", "bk"))

    @iso.function("iso", "probeA", reads=("A",))
    def probe_a(cap):
        cap.get("A", "x")        # 合法：在 reads 内
        cap.get("B", "y")        # 越权：B 不在 reads → 应抛
        return "unreachable"

    store = InMemoryGraphStore()
    store.put_object("A", "x", {"ak": "x"})
    overlay: list = []
    ctx = ActionContext(ontology_id="iso", params={}, actor=Actor("u", "tester"),
                        view=QueryView(store, overlay), overlay=overlay)
    cap = Capability(ctx, reg, action_def=ActionDef(name="act", namespace="iso", writes=("A",)))

    print("== 1. 租户/类型作用域 ==")
    print(f"  合法读 A: {cap.get('A', 'x')}")
    _expect_block("读未声明类型 Ghost（含跨租户）", lambda: cap.get("Ghost", "z"))

    print("== 2. 写声明强制（Action.writes=('A',)）==")
    cap.stage_write("A", "a1", {"ak": "a1"})
    print("  ✓ 允许写已声明的 A")
    _expect_block("写未声明的 B", lambda: cap.stage_write("B", "b1", {"bk": "b1"}))

    print("== 3. Function 最小权限（probeA.reads=('A',)）==")
    _expect_block("Function 内越权读 B", lambda: cap.call_function("probeA"))

    print("== 4. 能力收窄（内核内部不可达）==")
    for attr in ("view", "changeset", "store", "_base", "effects"):
        print(f"  cap.{attr} 暴露? {hasattr(cap, attr)}")
    assert not any(hasattr(cap, a) for a in ("view", "changeset", "store", "_base", "effects"))
    print("  ✓ 门面只暴露安全方法，内核内部不可达")


if __name__ == "__main__":
    main()
