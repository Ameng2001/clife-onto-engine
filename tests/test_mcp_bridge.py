"""治理写桥：写只经引擎、本体兜底、只反映已提交、读层解耦、无写旁路；JSON-RPC 适配。"""
from __future__ import annotations

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.mcp import GovernedBridge, Reflector
from clife_onto_engine.mcp.server import dispatch
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


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


def test_jsonrpc_dispatch_act_call_governed():
    br, _ = _bridge(enable_act=True)
    resp = dispatch(br, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                         "params": {"name": "act", "arguments": {
                             "action": "出一地一方",
                             "params": {"site_id": "parcel_001", "species": ["紫花苜蓿"]}}}})
    import json
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["kind"] == "rejected"               # 经引擎裁决，非 MCP 层旁路
