"""咨询路径 advise：只读建议、不写库/不审计、进记忆、序列化、不改既有路径、编译器认 advise。"""
from __future__ import annotations

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.memory import Layer
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Reply, Session
from clife_onto_engine.web import reply_to_json

import plugins.grass  # noqa: F401


class _C:
    def __init__(self, ci): self.ci = ci
    def compile(self, *a, **k): return self.ci


def _session(ci):
    store = InMemoryStore(); plugins.grass.seed_reference_data(store)
    return Session(ontology_id="grass", registry=spi.registry, store=store,
                   compiler=_C(ci), actor=Actor("u", "施工方"), session_id="a",
                   schema_version="grass@0.1.0", load_knowledge=True), store


def test_advise_is_readonly():
    s, store = _session(CompiledIntent("advise", confidence=0.8, answer="先改良再喷播"))
    r = s.ask("先做什么？")
    assert r.kind == "advise" and r.answer == "先改良再喷播"
    assert store.get_object("Project", "proj_parcel_001") is None       # 不写库
    assert len(s.engine.audit.query("grass")) == 0                      # 不进 Action 引擎/无审计


def test_advise_remembered():
    s, _ = _session(CompiledIntent("advise", confidence=0.8, answer="改良方案"))
    s.ask("怎么弄？")
    assert any(it.source == "advise" for it in s.memory.by_layer(Layer.CONTEXT, "grass", "a"))


def test_advise_serialized():
    out = reply_to_json(Reply("advise", 0.8, answer="建议内容"))
    assert out["kind"] == "advise" and out["answer"] == "建议内容"


def test_compiler_parses_advise():
    from clife_onto_engine.intent.compiler import IntentCompiler

    class _LLM:
        def complete_json(self, system, user):
            assert "advise" in system                                  # prompt 含 advise
            return {"kind": "advise", "answer": "先改良再喷播", "confidence": 0.8}
    ci = IntentCompiler(_LLM(), spi.registry).compile("grass", "先做什么？")
    assert ci.kind == "advise" and ci.answer == "先改良再喷播"


def test_action_query_unaffected():
    # advise 是新增第四类，做/查/澄清照旧
    s, _ = _session(CompiledIntent("clarify", confidence=0.4, question="补充信息"))
    assert s.ask("x").kind == "clarify"
