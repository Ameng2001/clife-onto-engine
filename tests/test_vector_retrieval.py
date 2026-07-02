"""Milvus 向量检索（方案 §5.9 指定库）：Milvus Lite 嵌入式跑通检索 + Session 换检索器无感。

pymilvus 是可选真后端（依赖较重：milvus-lite/faiss），未装则整文件跳过——与 Nebula 同待遇。
"""
from __future__ import annotations

import pytest

pytest.importorskip("pymilvus")  # 未装 pymilvus/milvus-lite → 跳过

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.retrieval import MilvusVectorRetriever
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401
from plugins.grass.corpus import CHUNKS


def _retriever(tmp_path):
    return MilvusVectorRetriever(CHUNKS, uri=str(tmp_path / "kb.db"))


def test_returns_sourced_hits_descending(tmp_path):
    r = _retriever(tmp_path)
    hits = r.retrieve("苜蓿 RFV 怎么分级", k=3)
    assert hits and len(hits) <= 3
    assert all(h.chunk.source for h in hits)                       # 出处保留（来源可查）
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)                  # COSINE 相似度降序
    assert any("NY/T 1574" in h.chunk.source for h in hits)        # RFV 查询召回分级标准


def test_k_limit_and_empty_query(tmp_path):
    r = _retriever(tmp_path)
    assert len(r.retrieve("盐碱地修复", k=1)) <= 1
    assert r.retrieve("", k=3) == []
    assert r.retrieve("   ", k=3) == []


def test_accepts_custom_real_shaped_embedder(tmp_path):
    # 真嵌入器形态 (list[str])->list[list[float]]（非 hashing_embed 对象）→ 走真嵌入分支
    from clife_onto_engine.retrieval import hashing_embed
    custom = lambda texts: hashing_embed(texts, 32)        # noqa: E731
    r = MilvusVectorRetriever(CHUNKS, embed=custom, dim=32, uri=str(tmp_path / "kb.db"))
    hits = r.retrieve("苜蓿 RFV 分级", k=2)
    assert hits and all(h.chunk.source for h in hits)


def test_same_protocol_swaps_into_session(tmp_path):
    r = _retriever(tmp_path)

    class _Stub:
        def compile(self, ns, utt, *, memory_text="", actor_role=None):
            assert "检索资料" in memory_text                        # 向量检索资料注入了上下文
            return CompiledIntent("advise", confidence=0.9, answer="见资料")

    session = Session(ontology_id="grass", registry=spi.registry, store=InMemoryStore(),
                      compiler=_Stub(), actor=Actor("u1", "施工方"), retriever=r)
    reply = session.ask("盐碱地怎么修复、选什么草种？")
    assert reply.kind == "advise" and reply.sources           # 出处流转（来源可查）
