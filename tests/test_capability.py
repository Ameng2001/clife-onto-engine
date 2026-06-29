"""Capability 沙箱：租户/类型作用域、写声明强制、Function 最小权限、能力收窄。"""
from __future__ import annotations

import pytest

from clife_onto_engine.metamodel import ActionDef
from clife_onto_engine.query import InMemoryStore, QueryView
from clife_onto_engine.sdk import Capability, CapabilityError, ObjectType, Registry, SPI
from clife_onto_engine.sdk.context import ActionContext, Actor


def _cap(writes=("A",), reads_fn=("A",)):
    iso = SPI(Registry())
    reg = iso.registry
    reg.add_object(ObjectType("A", "iso", "ak"))
    reg.add_object(ObjectType("B", "iso", "bk"))

    @iso.function("iso", "probeA", reads=reads_fn)
    def _probe(cap):
        cap.get("A", "x")
        cap.get("B", "y")   # 越权（B 不在 reads）
        return "unreachable"

    store = InMemoryStore()
    store.put_object("A", "x", {"ak": "x"})
    overlay: list = []
    ctx = ActionContext(ontology_id="iso", params={}, actor=Actor("u", "t"),
                        view=QueryView(store, overlay), overlay=overlay)
    return Capability(ctx, reg, action_def=ActionDef(name="act", namespace="iso", writes=writes))


def test_scope_blocks_undeclared_type():
    cap = _cap()
    assert cap.get("A", "x") == {"ak": "x"}
    with pytest.raises(CapabilityError):
        cap.get("Ghost", "z")


def test_write_declaration_enforced():
    cap = _cap(writes=("A",))
    cap.stage_write("A", "a1", {"ak": "a1"})           # 声明内，放行
    with pytest.raises(CapabilityError):
        cap.stage_write("B", "b1", {"bk": "b1"})        # 未声明写


def test_function_least_privilege():
    cap = _cap(reads_fn=("A",))
    with pytest.raises(CapabilityError):
        cap.call_function("probeA")                     # 函数内越权读 B


def test_kernel_internals_not_exposed():
    cap = _cap()
    for attr in ("view", "changeset", "store", "_base"):
        assert not hasattr(cap, attr)
