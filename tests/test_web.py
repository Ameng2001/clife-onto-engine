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
