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


# ---- 嵌入函数（可插拔）：离线确定性默认 + 真模型 opt-in --------------------
def hashing_embed(texts, dim: int = 64) -> list:
    """离线确定性嵌入：字符 bigram 经 md5 特征哈希入固定维、L2 归一。

    无模型、无网络、跨进程确定（不用 salted 的内置 hash）——让向量检索**管道**可 CI 测。
    诚实边界：它≈词法，**不解决同义词**（霉变/霉菌）；真语义需换真嵌入模型（下）。
    真模型 opt-in：传 `embed=` 一个 `(list[str])->list[list[float]]`，如 BGE-M3 / DashScope
    text-embedding（复用 openai 兼容客户端）。协议一致，检索器无感。
    """
    import hashlib
    import math

    out = []
    for t in texts:
        vec = [0.0] * dim
        for bg in _bigrams(t):
            h = int.from_bytes(hashlib.md5(bg.encode("utf-8")).digest()[:4], "big")
            vec[h % dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        out.append([x / norm for x in vec])
    return out


class DashScopeEmbedder:
    """真嵌入模型（DashScope text-embedding，OpenAI 兼容端点）——让向量检索有真语义。

    是 `embed` 的一个 opt-in 真实现：`(list[str]) -> list[list[float]]`。复用 llm 的配置
    （env DASHSCOPE_*/OPENAI_* 或 llm.local.json）。真语义 → 同义词可召回（霉变↔霉菌），
    这是离线 hashing_embed（≈词法）给不了的。需 API key + 网络，故不进 CI（同 real-Qwen）。

      e = DashScopeEmbedder(dimensions=1024)
      r = MilvusVectorRetriever(CHUNKS, embed=e, dim=e.dim)   # dim 与嵌入维一致
    """

    def __init__(self, *, model: str = "text-embedding-v3", dimensions: int = 1024,
                 config_path: str = "llm.local.json", base_url=None, api_key=None,
                 batch_size: int = 10) -> None:
        from .intent.llm import _load_config  # 复用 env/本地文件配置加载

        cfg = _load_config(config_path)
        self.model = model
        self.dim = dimensions
        self._batch = batch_size
        base = base_url or cfg["base_url"] or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        key = api_key or cfg["api_key"]
        if not key:
            raise RuntimeError("嵌入需 api_key（env DASHSCOPE_API_KEY/OPENAI_API_KEY 或 llm.local.json）")
        from openai import OpenAI
        self._client = OpenAI(base_url=base, api_key=key)

    def __call__(self, texts) -> list:
        out: list = []
        for i in range(0, len(texts), self._batch):          # 分批：嵌入端点有单次条数上限
            kwargs = {"model": self.model, "input": list(texts[i:i + self._batch])}
            if self.dim:
                kwargs["dimensions"] = self.dim
            resp = self._client.embeddings.create(**kwargs)
            out.extend(d.embedding for d in resp.data)
        return out


class MilvusVectorRetriever:
    """Milvus 向量检索（方案 §5.9 指定库）。同 KnowledgeRetriever 协议——Session 换检索器无感。

    嵌入式 **Milvus Lite**（uri=本地 .db 文件，进程内、无服务器、可 CI）与真 **Milvus 服务器**
    （uri=http://host:19530）**同一份代码**，只换 uri。向量入库、COSINE 检索、带出处返回。
    嵌入用可插拔 `embed`（默认 hashing_embed 离线；真部署换真模型）。
    """

    def __init__(self, chunks, *, embed=hashing_embed, dim: int = 64,
                 uri: str = "./milvus_kb.db", collection: str = "kb", client=None) -> None:
        from pymilvus import MilvusClient  # 延迟导入：未装 pymilvus 不影响引擎其它部分

        self._embed = embed
        self._dim = dim
        self._collection = collection
        self._client = client or MilvusClient(uri)
        if self._client.has_collection(collection):
            self._client.drop_collection(collection)          # 幂等重建（检索器绑定固定语料）
        self._client.create_collection(collection, dimension=dim, metric_type="COSINE", auto_id=False)
        chunks = list(chunks)
        if chunks:
            vecs = embed([c.text + " " + " ".join(c.refs) for c in chunks], dim) \
                if embed is hashing_embed else embed([c.text + " " + " ".join(c.refs) for c in chunks])
            rows = [{"id": i, "vector": v, "doc_id": c.doc_id, "text": c.text,
                     "source": c.source, "refs": "|".join(c.refs)}
                    for i, (c, v) in enumerate(zip(chunks, vecs))]
            self._client.insert(collection, rows)

    def retrieve(self, query: str, k: int = 3) -> list:
        if not (query and query.strip()):
            return []
        qv = self._embed([query], self._dim)[0] if self._embed is hashing_embed else self._embed([query])[0]
        res = self._client.search(self._collection, data=[qv], limit=k,
                                  output_fields=["doc_id", "text", "source", "refs"])
        hits = []
        for h in (res[0] if res else []):
            e = h["entity"]
            refs = tuple(r for r in (e.get("refs") or "").split("|") if r)
            hits.append(DocHit(DocChunk(e["doc_id"], e["text"], e["source"], refs), float(h["distance"])))
        return hits
