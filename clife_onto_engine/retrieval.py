"""知识检索（RAG · advise 通道）—— 对非结构化文档全文的只读检索。

这是**第四条知识通道**（前三条：规则 source/citations、对象附着知识、动作 evidence 血统）。
定位（对齐"OAG 主机制 / RAG 仅服务 advise"）：
  · **只服务 advise 开放问答**——检索标准/案例等文档段落、每段带出处，注入上下文供 LLM 接地；
  · **结果绝不驱动写入**——写入只经 Action 引擎；防幻觉在执行层（OAG），检索只做取证补充。

内核只定义**协议 + 离线确定性默认实现**（InMemoryRetriever：字符 bigram 重合打分，无外部依赖、
可 CI 测、脱网可跑）。真向量库（Milvus/pgvector + embedding）作 opt-in 适配器接同一协议
（与 GraphStore / nebula_store 同构：换实现，Session/advise 无感）。行业无关（CI 强制）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DocChunk:
    """一段可检索的文档全文块。source 是出处（标准号/案例 ID/文档段）→ 支撑"来源可查"。"""
    doc_id: str
    text: str
    source: str
    refs: tuple = ()


@dataclass(frozen=True)
class DocHit:
    chunk: DocChunk
    score: float


class KnowledgeRetriever(Protocol):
    """检索协议：给查询、返回带出处的相关文档块（按相关性降序）。"""
    def retrieve(self, query: str, k: int = 3) -> list: ...


def _bigrams(s: str) -> set:
    s = "".join(s.split())
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


class InMemoryRetriever:
    """离线确定性检索：字符 bigram 重合计数打分。

    非要替代生产向量检索，而是给同协议的**离线默认**——CI 与脱网 demo 可跑，真部署换成
    向量适配器即可。打分确定性（分降序、doc_id 升序 tie-break），无 wall clock / 随机。
    """

    def __init__(self, chunks) -> None:
        self._chunks = list(chunks)

    def retrieve(self, query: str, k: int = 3) -> list:
        qb = _bigrams(query)
        if not qb:
            return []
        hits = []
        for c in self._chunks:
            hay = _bigrams(c.text + " " + " ".join(c.refs))
            score = len(qb & hay)
            if score > 0:
                hits.append(DocHit(c, float(score)))
        hits.sort(key=lambda h: (-h.score, h.chunk.doc_id))
        return hits[:k]
