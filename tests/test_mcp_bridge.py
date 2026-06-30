"""治理写桥：写只经引擎、本体兜底、只反映已提交、读层解耦、无写旁路；JSON-RPC 适配。"""
from __future__ import annotations

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.mcp import GovernedBridge, Reflector
from clife_onto_engine.mcp.server import dispatch
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401

from clife_onto_engine.metamodel import LinkType, ObjectType, ParamSpec
from clife_onto_engine.sdk.errors import RegistrationError

# 测试内最小本体 reltest：一个写关系的 Action，验证关系反映（不碰 grass 插件）。
_RELNS = "reltest"
try:
    spi.registry.add_object(ObjectType(name="A", namespace=_RELNS, primary_key="a_id"))
    spi.registry.add_object(ObjectType(name="B", namespace=_RELNS, primary_key="b_id"))
    spi.registry.add_link(LinkType("rel", _RELNS, "A", "B"))

    @spi.action(_RELNS, "link_them", params=(ParamSpec("a", "string"), ParamSpec("b", "string")),
                writes=("A", "B"))
    def _link_them(ctx):
        a, b = ctx.params["a"], ctx.params["b"]
        ctx.stage_write("A", a, {"a_id": a})
        ctx.stage_write("B", b, {"b_id": b})
        ctx.stage_link("rel", "A", a, "B", b)
        ctx.set_confidence(0.9)
except RegistrationError:
    pass  # 已注册（pytest 重复导入兜底）


class _NoCompiler:
    pass


def _bridge(enable_act=True, post=None):
    store = InMemoryStore()
    plugins.grass.seed_reference_data(store)
    rec = []
    if post is None:
        def post(url, payload):
            rec.append(payload); return {"accepted": len(payload.get("entities", []))}
    br = GovernedBridge(ontology_id="grass", registry=spi.registry, store=store,
                        compiler=_NoCompiler(), actor=Actor("u1", "施工方"),
                        engine=ActionEngine(spi.registry, store=store),
                        reflector=Reflector("http://r.local", "grass", post=post),
                        enable_act=enable_act)
    return br, rec


def test_committed_reflects_with_hex_ids():
    br, rec = _bridge()
    r = br.act("出一地一方", {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300})
    assert r["kind"] == "committed" and r["reflected"] >= 1
    eid = rec[0]["entities"][0]["__entity_id__"]
    assert len(eid) == 32 and all(c in "0123456789abcdef" for c in eid)


def test_governed_rejection_blocks_reflection():
    br, rec = _bridge()
    r = br.act("出一地一方", {"site_id": "parcel_001", "species": ["紫花苜蓿"], "budget": 300})
    assert r["kind"] == "rejected"
    assert any(v["rule"] == "乡土合规" for v in r["violations"])
    assert rec == []                                  # 本体兜底：违规不进读层


def test_hil_pending_not_reflected():
    # 低置信触发 HIL（动作 handler 读 _confidence，predicate: <0.75 → HIL）
    br, rec = _bridge()
    r = br.act("出一地一方",
               {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300, "_confidence": 0.5})
    assert r["kind"] == "pending_hil" and r["reflected"] == 0
    assert rec == []                                  # 待人工复核，读层不反映


def test_reflection_failure_does_not_rollback_commit():
    def boom(url, payload):
        raise ConnectionError("down")
    br, _ = _bridge(post=boom)
    r = br.act("出一地一方", {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300})
    assert r["kind"] == "committed" and "reflect_error" in r


def test_act_opt_in_and_no_write_bypass():
    br, rec = _bridge(enable_act=False)
    assert "act" not in br.tools()
    assert br.act("出一地一方", {})["kind"] == "error"
    assert rec == []
    br2, _ = _bridge(enable_act=True)
    assert set(br2.tools()) <= {"query", "act"}        # 只受治理工具，无 UModel 写旁路


def test_jsonrpc_dispatch_tools_list_respects_opt_in():
    br, _ = _bridge(enable_act=False)
    resp = dispatch(br, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {"query"}                          # 默认只读
    br2, _ = _bridge(enable_act=True)
    resp2 = dispatch(br2, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert {t["name"] for t in resp2["result"]["tools"]} == {"query", "act"}


def _reltest_bridge():
    from clife_onto_engine.umodel import _eid
    store = InMemoryStore()
    rec = {"entities": [], "relations": []}

    def post(url, payload):
        if url.endswith("entities:write"):
            rec["entities"].extend(payload["entities"])
        elif url.endswith("relations:write"):
            rec["relations"].extend(payload["relations"])
        return {"accepted": 1}

    br = GovernedBridge(ontology_id="reltest", registry=spi.registry, store=store,
                        compiler=_NoCompiler(), actor=Actor("u1", "tester"),
                        engine=ActionEngine(spi.registry, store=store),
                        reflector=Reflector("http://r.local", "reltest", post=post),
                        enable_act=True)
    return br, rec, _eid


def test_committed_relation_exposed_and_reflected():
    br, rec, _eid = _reltest_bridge()
    r = br.act("link_them", {"a": "a1", "b": "b1"})
    assert r["kind"] == "committed"
    # ActionResult 暴露已提交关系
    assert ["rel", "A", "a1", "B", "b1"] in r["links_written"]
    assert r.get("relations_reflected") == 1
    # 反映的关系两端 id 与对象反映同公式（引用闭合）
    rel = rec["relations"][0]
    assert rel["__relation_type__"] == "rel"
    assert rel["__src_entity_id__"] == _eid("reltest", "A", "a1")
    assert rel["__dest_entity_id__"] == _eid("reltest", "B", "b1")
    # 两端实体也已反映，且 id 一致
    eids = {e["__entity_id__"] for e in rec["entities"]}
    assert rel["__src_entity_id__"] in eids and rel["__dest_entity_id__"] in eids


def test_jsonrpc_dispatch_act_call_governed():
    br, _ = _bridge(enable_act=True)
    resp = dispatch(br, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": "act", "arguments": {
                             "action": "出一地一方",
                             "params": {"site_id": "parcel_001", "species": ["紫花苜蓿"]}}}})
    import json
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["kind"] == "rejected"               # 经引擎裁决，非 MCP 层旁路
