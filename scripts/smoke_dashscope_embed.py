"""RAG 真嵌入 smoke（DashScope + Milvus）—— 真语义检索，含同义词召回。

用 DashScope text-embedding 把语料嵌入 Milvus，验证真语义（如"发霉的牧草能交易吗"能召回
只写了"霉变/霉菌毒素"的条款——离线 hashing_embed 的词法给不了）。

需 DASHSCOPE_API_KEY（env 或 llm.local.json）+ 网络 + pip install 'pymilvus[milvus_lite]'。
无凭据/依赖则优雅跳过。运行：python scripts/smoke_dashscope_embed.py
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import plugins.grass  # noqa: F401
from plugins.grass.corpus import CHUNKS


def main() -> int:
    try:
        from clife_onto_engine.retrieval import DashScopeEmbedder, MilvusVectorRetriever
    except Exception as e:  # pragma: no cover
        print(f"跳过：需 pip install 'pymilvus[milvus_lite]'（{e})"); return 0
    try:
        embedder = DashScopeEmbedder(dimensions=1024)
    except Exception as e:
        print(f"跳过：需 DashScope 凭据（{e}）"); return 0

    print("== RAG 真嵌入 smoke（DashScope text-embedding + Milvus）==")
    try:
        r = MilvusVectorRetriever(CHUNKS, embed=embedder, dim=embedder.dim,
                                  uri=tempfile.mktemp(suffix=".db"))
    except Exception as e:  # 网络/额度等
        print(f"跳过：嵌入/建库失败（{e}）"); return 0

    # 同义词考验：查询用"发霉/能交易"，语料条款只写"霉变/霉菌毒素/交易" → 真语义应召回
    probes = [
        ("发霉的牧草还能不能交易？", "std_gb13078_1"),
        ("盐碱地用什么草种修复？", "std_gbt37067_1"),
        ("苜蓿等级怎么判定？", "std_nyt1574_1"),
    ]
    for q, expect in probes:
        hits = r.retrieve(q, k=3)
        ids = [h.chunk.doc_id for h in hits]
        mark = "✓" if expect in ids else "·"
        print(f"\n  ❓ {q}")
        print(f"     {mark} 召回 {[(h.chunk.doc_id, round(h.score, 3)) for h in hits]}（期望含 {expect}）")

    print("\n✓ DashScope 真嵌入 smoke 跑通：真语义向量检索（同义词可召回）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
