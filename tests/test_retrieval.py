"""RAG · advise 通道：离线检索确定性 + Session advise 接地与出处流转。"""
from __future__ import annotations

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.retrieval import DocChunk, InMemoryRetriever
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401
from plugins.grass.corpus import CHUNKS

_R = InMemoryRetriever(CHUNKS)


def test_retriever_deterministic_and_ranked():
    hits = _R.retrieve("盐碱地怎么选草种修复", k=3)
    assert hits, "相关查询应召回文档"
    ids = [h.chunk.doc_id for h in hits]
    # 盐碱/修复/草种相关块应在前；分数降序、doc_id 升序 tie-break（确定性）
    assert "std_gbt37067_1" in ids or "case_盐碱_001" in ids
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    # 每块带出处（来源可查）
    assert all(h.chunk.source for h in hits)


def test_retriever_no_match_and_k_limit():
    assert _R.retrieve("zzz totally unrelated latin", k=3) == []   # 无 bigram 重合 → 空
    assert _R.retrieve("", k=3) == []                              # 空查询 → 空
    assert len(_R.retrieve("盐碱苜蓿修复", k=1)) <= 1               # k 限制生效


class _StubCompiler:
    """离线桩编译器：把上下文回显为 advise 答案，用来断言检索资料确实注入了。"""
    def __init__(self):
        self.seen_context = ""

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        self.seen_context = memory_text
        return CompiledIntent("advise", confidence=0.9, answer="见检索资料")


def test_session_advise_injects_retrieval_and_surfaces_sources():
    stub = _StubCompiler()
    session = Session(ontology_id="grass", registry=spi.registry, store=InMemoryStore(),
                      compiler=stub, actor=Actor("u1", "施工方"), retriever=_R)
    reply = session.ask("盐碱地怎么修复、选什么草种？")
    assert reply.kind == "advise"
    # 检索资料注入了上下文（含出处标记）
    assert "检索资料" in stub.seen_context and "出处" in stub.seen_context
    # 出处流转到 Reply（来源可查），且去重保序
    assert reply.sources and len(set(reply.sources)) == len(reply.sources)
    assert any("GB/T 37067" in s or "case_盐碱_001" in s for s in reply.sources)


def test_session_advise_without_retriever_still_works():
    """未接 retriever 时 advise 照常（向后兼容），sources 为空。"""
    stub = _StubCompiler()
    session = Session(ontology_id="grass", registry=spi.registry, store=InMemoryStore(),
                      compiler=stub, actor=Actor("u1", "施工方"))
    reply = session.ask("盐碱地怎么修复？")
    assert reply.kind == "advise" and reply.sources == ()
    assert "检索资料" not in stub.seen_context
