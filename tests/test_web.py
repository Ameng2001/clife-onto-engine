"""HTTP API（FastAPI）—— 注入 stub compiler，无需 LLM/网络即可测路由与序列化。

fastapi 未安装时整文件跳过（CI 不装 fastapi）。
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from clife_onto_engine.intent.compiler import CompiledIntent  # noqa: E402
from clife_onto_engine.query.oql import Cond, OQLQuery  # noqa: E402
from clife_onto_engine.sdk import Actor, spi  # noqa: E402
from clife_onto_engine.web import create_app  # noqa: E402


class _StubCompiler:
    """确定性桩：含"哪些"→查询，含"出"→动作，否则澄清。不联网。"""

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        if "哪些" in utterance:
            q = OQLQuery(namespace=ontology_id, start="Site", where=(Cond("region", "eq", "巴彦淖尔"),))
            return CompiledIntent("query", oql=q, confidence=0.9)
        if utterance.startswith("出"):
            return CompiledIntent("action", action="出一地一方",
                                  params={"site_id": "parcel_001", "species": ["碱茅"], "budget": 100},
                                  confidence=0.9)
        return CompiledIntent("clarify", question="请补充信息", confidence=0.4)


def _store():
    from clife_onto_engine.query import InMemoryStore
    from plugins.grass import seed_reference_data
    s = InMemoryStore()
    s.put_object("Site", "parcel_001", {"parcel_id": "parcel_001", "region": "巴彦淖尔", "site_type": "盐碱"})
    seed_reference_data(s)  # 乡土名录（动作用）
    return s


@pytest.fixture
def client():
    app = create_app(
        ontologies={"grass": {"store": _store(), "actor": Actor("u1", "施工方")}},
        make_compiler=lambda: _StubCompiler(),
    )
    return TestClient(app)


def test_health_and_ontologies(client):
    assert client.get("/health").json()["status"] == "ok"
    assert "grass" in client.get("/ontologies").json()["ontologies"]


def test_root_landing_and_favicon(client):
    r = client.get("/")
    assert r.status_code == 200 and "数智本体引擎" in r.text
    assert "/docs" in r.text and "/explorer/grass" in r.text   # 端点索引 + 本体直达
    assert "打开对象图" in r.text                               # Explorer 作醒目主入口（卡片）
    assert client.get("/favicon.ico").status_code == 204        # 消 404 噪声（公开，不需认证）


def test_manifest(client):
    m = client.get("/manifest/grass").json()
    assert m["ontology_id"] == "grass"
    assert any(a["name"] == "出一地一方" for a in m["actions"])


def test_unknown_ontology_404(client):
    assert client.get("/manifest/medical").status_code == 404


def test_ask_query(client):
    r = client.post("/ask", json={"ontology": "grass", "utterance": "巴彦淖尔有哪些地块？"}).json()
    assert r["kind"] == "query"
    assert {row["parcel_id"] for row in r["rows"]} == {"parcel_001"}


def test_ask_action_commit(client):
    r = client.post("/ask", json={"ontology": "grass", "utterance": "出一地一方"}).json()
    assert r["kind"] == "committed"
    assert ["SeedPack", "sp_parcel_001"] in r["written"]


def test_ask_clarify(client):
    r = client.post("/ask", json={"ontology": "grass", "utterance": "随便说说"}).json()
    assert r["kind"] == "clarify" and r["question"]


def test_plan_endpoint(client):
    r = client.post("/plan", json={"ontology": "grass", "object_type": "Site",
                                   "key": "parcel_001", "series": "soil_moisture"}).json()
    assert r["ok"] and r["provider"] == "prometheus"
    assert 'parcel="parcel_001"' in r["plan"] and "$parcel" not in r["plan"]


def test_plan_endpoint_structured_error(client):
    # 不存在的实例 → build_plan 结构化 error 透传
    r = client.post("/plan", json={"ontology": "grass", "object_type": "Site",
                                   "key": "nope", "series": "soil_moisture"}).json()
    assert r["ok"] is False and "不存在" in r["error"]


def test_plan_unknown_ontology_404(client):
    assert client.post("/plan", json={"ontology": "medical", "object_type": "X",
                                      "key": "y", "series": "z"}).status_code == 404


def test_plan_log_with_params(client):
    r = client.post("/plan", json={"ontology": "grass", "object_type": "Site",
                                   "key": "parcel_001", "series": "iot_alerts",
                                   "params": {"level": "ERROR", "since": "now-1h"}}).json()
    assert r["ok"] and r["provider"] == "elasticsearch" and r["kind"] == "log"
    assert '"level":"ERROR"' in r["plan"] and "$" not in r["plan"]


def test_explorer_endpoint():
    from clife_onto_engine.web import create_app
    app = create_app(
        ontologies={"grass": {"store": _store(), "actor": Actor("u1", "施工方")}},
        make_compiler=lambda: _StubCompiler(), explorer_js="/*CY*/1;",
    )
    c = TestClient(app)
    r = c.get("/explorer/grass")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Site:parcel_001" in r.text and "/*CY*/" in r.text  # 活对象图 + 注入 JS 内联
    assert "soil_moisture" in r.text and "取计划" in r.text     # 遥测联动（点对象取计划）
    assert c.get("/explorer/medical").status_code == 404


def test_tenant_boundary_enforced():
    from clife_onto_engine.web import create_app
    from clife_onto_engine.authz import TenantAccessPolicy
    policy = TenantAccessPolicy(default_allow=False).grant("A", "grass")
    app = create_app(
        ontologies={"grass": {"store": _store(), "actor": Actor("u1", "施工方")}},
        make_compiler=lambda: _StubCompiler(), tenant_policy=policy)
    c = TestClient(app)
    # 授权租户放行
    assert c.post("/ask", json={"ontology": "grass", "utterance": "巴彦淖尔有哪些地块？",
                                "tenant": "A"}).status_code == 200
    # 未授权租户 403（跨租户，入口拒）
    assert c.post("/ask", json={"ontology": "grass", "utterance": "x", "tenant": "B"}).status_code == 403
    # GET 端点走 tenant 查询参数
    assert c.get("/manifest/grass?tenant=A").status_code == 200
    assert c.get("/manifest/grass?tenant=B").status_code == 403
    assert c.get("/explorer/grass?tenant=B").status_code == 403


def test_no_tenant_policy_backward_compatible():
    # 无 tenant_policy：不校验租户（既有行为）
    r = client_noop().post("/ask", json={"ontology": "grass", "utterance": "巴彦淖尔有哪些地块？"})
    assert r.status_code == 200


def client_noop():
    from clife_onto_engine.web import create_app
    app = create_app(ontologies={"grass": {"store": _store(), "actor": Actor("u1", "施工方")}},
                     make_compiler=lambda: _StubCompiler())
    return TestClient(app)


def _app_with_identity():
    from clife_onto_engine.web import create_app
    from clife_onto_engine.identity import StaticIdentityResolver
    from clife_onto_engine.authz import TenantAccessPolicy
    resolver = (StaticIdentityResolver()
                .add("k-A-worker", "A", "u1", "施工方")
                .add("k-B", "B", "u2", "施工方"))
    tenant_policy = TenantAccessPolicy(default_allow=False).grant("A", "grass")
    return create_app(
        ontologies={"grass": {"store": _store(), "actor": Actor("u0", "施工方")}},
        make_compiler=lambda: _StubCompiler(),
        tenant_policy=tenant_policy, identity_resolver=resolver)


def test_missing_or_bad_credential_401():
    c = TestClient(_app_with_identity())
    assert c.post("/ask", json={"ontology": "grass", "utterance": "巴彦淖尔有哪些地块？"}).status_code == 401
    assert c.post("/ask", json={"ontology": "grass", "utterance": "x"},
                  headers={"X-Api-Key": "nope"}).status_code == 401
    assert c.get("/manifest/grass").status_code == 401


def test_authenticated_tenant_drives_boundary():
    c = TestClient(_app_with_identity())
    # A 认证 → grass 放行
    assert c.post("/ask", json={"ontology": "grass", "utterance": "巴彦淖尔有哪些地块？"},
                  headers={"X-Api-Key": "k-A-worker"}).status_code == 200
    # B 认证 → grass 未授权 → 403（用认证 tenant，非声明）
    assert c.post("/ask", json={"ontology": "grass", "utterance": "x", "tenant": "A"},
                  headers={"X-Api-Key": "k-B"}).status_code == 403


def test_authenticated_actor_drives_action():
    # 认证角色=施工方 → /ask 触发动作可 commit（StubCompiler "出"→动作）
    c = TestClient(_app_with_identity())
    r = c.post("/ask", json={"ontology": "grass", "utterance": "出方案"},
               headers={"X-Api-Key": "k-A-worker"}).json()
    assert r["kind"] == "committed"


def _app_with_authz():
    """authz 授权门经 create_app 注入 engine：出一地一方 仅授予施工方。"""
    from clife_onto_engine.authz import AuthzPolicy
    from clife_onto_engine.identity import StaticIdentityResolver
    resolver = (StaticIdentityResolver()
                .add("k-worker", "A", "u1", "施工方")
                .add("k-guest", "A", "u9", "游客"))
    authz = AuthzPolicy(default_allow=False).grant("grass", "出一地一方", "施工方")
    return create_app(
        ontologies={"grass": {"store": _store(), "actor": Actor("u0", "施工方")}},
        make_compiler=lambda: _StubCompiler(), identity_resolver=resolver, authz=authz)


def test_authz_gate_wired_through_create_app():
    c = TestClient(_app_with_authz())
    # 施工方（授权）→ 动作提交
    ok = c.post("/ask", json={"ontology": "grass", "utterance": "出方案"},
                headers={"X-Api-Key": "k-worker"}).json()
    assert ok["kind"] == "committed"
    # 游客（未授权该动作）→ phase=authz 拒（授权门经 create_app 接进 engine）
    no = c.post("/ask", json={"ontology": "grass", "utterance": "出方案"},
                headers={"X-Api-Key": "k-guest"}).json()
    assert no["kind"] == "rejected"
    assert any(v["rule"] == "authz" for v in no["violations"])
