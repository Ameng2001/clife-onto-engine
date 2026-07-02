"""RAG 真向量检索 smoke（Milvus）—— 方案 §5.9 指定库，嵌入式 Milvus Lite 跑通。

同 KnowledgeRetriever 协议：把离线 InMemoryRetriever 换成 MilvusVectorRetriever，Session 无感。
嵌入用离线 hashing_embed（管道可跑；真语义换真嵌入模型 opt-in）。需 pip install
'pymilvus[milvus_lite]'。运行：python scripts/smoke_vector_rag.py
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

try:
    from clife_onto_engine.retrieval import MilvusVectorRetriever
except Exception as e:  # pragma: no cover
    print(f"跳过：需 pip install 'pymilvus[milvus_lite]'（{e}）")
    raise SystemExit(0)

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401
from plugins.grass.corpus import CHUNKS


class _Stub:
    def compile(self, ns, utt, *, memory_text="", actor_role=None):
        return CompiledIntent("advise", confidence=0.9, answer="综合向量检索资料给出只读建议")


def main() -> int:
    retriever = MilvusVectorRetriever(CHUNKS, uri=tempfile.mktemp(suffix=".db"))
    print("== RAG 真向量 smoke（Milvus Lite 嵌入式）==")
    fails = 0
    for q in ["盐碱地怎么修复、选什么草种？", "苜蓿 RFV 怎么分级？"]:
        hits = retriever.retrieve(q, k=2)
        s = Session(ontology_id="grass", registry=spi.registry, store=InMemoryStore(),
                    compiler=_Stub(), actor=Actor("u1", "施工方"), retriever=retriever)
        reply = s.ask(q)
        ok = reply.kind == "advise" and bool(reply.sources)
        fails += not ok
        print(f"\n  ❓ {q}")
        print(f"     向量召回：{[(h.chunk.doc_id, round(h.score, 3)) for h in hits]}")
        print(f"     {'✓' if ok else '✗'} advise · 出处：{list(reply.sources)}")

    if fails:
        print(f"\n✗ RAG 真向量 smoke 失败（{fails}）"); return 1
    print("\n✓ RAG 真向量 smoke 全通过：Milvus 检索带出处、同协议换检索器无感（真语义换真嵌入模型）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
