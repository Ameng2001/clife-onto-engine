"""知识影响力对比：SpyCompiler 验"知识到达 LLM 的 memory_text"（管道）；行为差异需真 Qwen。"""
from __future__ import annotations

from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

from scripts.e2e_harness import ScriptedCompiler, seed
from scripts.e2e_knowledge_influence import UTTERANCES, SpyCompiler

import plugins.grass  # noqa: F401

_KN = ("处置手册", "改良", "盐碱化多因")


def _run(load_knowledge, sid):
    spy = SpyCompiler(ScriptedCompiler())
    s = Session(ontology_id="grass", registry=spi.registry, store=seed(),
                compiler=spy, actor=Actor("u1", "施工方"), session_id=sid,
                schema_version="grass@0.1.0", load_knowledge=load_knowledge)
    for u in UTTERANCES:
        s.ask(u)
    return spy


def test_knowledge_reaches_llm_when_on():
    spy = _run(True, "on")
    assert any(any(w in c["memory_text"] for w in _KN) for c in spy.calls)


def test_no_knowledge_when_off():
    spy = _run(False, "off")
    assert not any(any(w in c["memory_text"] for w in _KN) for c in spy.calls)


def test_spy_records_each_compile():
    spy = _run(True, "on2")
    assert len(spy.calls) == len(UTTERANCES)
    assert all("memory_text" in c and "utterance" in c for c in spy.calls)
