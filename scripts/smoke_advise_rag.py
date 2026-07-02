"""RAG · advise 通道 smoke —— 离线演示：开放问答检索非结构化全文、答案带出处。

展示第四条知识通道：advise 经 InMemoryRetriever 检索标准/案例段落、注入上下文、出处流转到回复；
只读、不驱动写入（写入仍只经 Action 引擎）。全离线、无 LLM（用桩编译器回显）。

运行：python scripts/smoke_advise_rag.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.retrieval import InMemoryRetriever
from clife_onto_engine.session import Session
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401
from plugins.grass.corpus import CHUNKS


class _StubCompiler:
    """桩：把检索到的资料回显为 advise 建议（真部署换成 Qwen 意图编译器）。"""
    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        answer = "综合检索资料给出只读建议（真部署由 LLM 据资料生成）"
        return CompiledIntent("advise", confidence=0.9, answer=answer)


def main() -> int:
    retriever = InMemoryRetriever(CHUNKS)
    session = Session(ontology_id="grass", registry=spi.registry, store=InMemoryStore(),
                      compiler=_StubCompiler(), actor=Actor("u1", "施工方"), retriever=retriever)

    questions = [
        "盐碱地怎么修复、选什么草种？",
        "苜蓿 RFV 怎么分级？",
        "霉变的草还能卖吗？",
    ]
    print("== RAG · advise 通道 smoke（离线）==")
    fails = 0
    for q in questions:
        hits = retriever.retrieve(q, k=3)
        reply = session.ask(q)
        ok = reply.kind == "advise" and bool(reply.sources)
        fails += not ok
        print(f"\n  ❓ {q}")
        print(f"     检索命中 {len(hits)} 段：{[h.chunk.doc_id for h in hits]}")
        print(f"     {'✓' if ok else '✗'} advise · 出处：{list(reply.sources)}")

    # 关键不变量：advise 只读——不写库
    store = InMemoryStore()
    s2 = Session(ontology_id="grass", registry=spi.registry, store=store,
                 compiler=_StubCompiler(), actor=Actor("u1", "施工方"), retriever=retriever)
    s2.ask("盐碱地怎么修复？")
    wrote = sum(1 for _ in store.iter_objects("Project")) + sum(1 for _ in store.iter_objects("SeedPack"))
    ro_ok = wrote == 0
    fails += not ro_ok
    print(f"\n  {'✓' if ro_ok else '✗'} 只读不变量：advise 未写任何 Project/SeedPack（写入只经 Action 引擎）")

    if fails:
        print(f"\n✗ RAG·advise smoke 失败（{fails}）"); return 1
    print("\n✓ RAG·advise 通道 smoke 全通过：开放问答检索全文、答案带出处、只读不写库")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
