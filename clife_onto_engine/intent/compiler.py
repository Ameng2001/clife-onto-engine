"""意图编译器 —— 自然语言 → 受约束、可校验的结构化意图（Action / 澄清 / 拒绝）。

纪律：**LLM 只在能力清单内提议，内核确定性校验**（动作存在、参数名⊆声明、必填齐全）。
未知动作/越界参数一律拒（防注入 + schema 落地）；信息不足走澄清；低置信走澄清/HIL。
这把"通用模型会说"约束成"在能力清单内选一个受治理的操作"——这是 OAG（本体增强生成·
行动增强），不是 RAG/Graph-RAG。防幻觉发生在**执行层**（引擎 guard/写后规则/确定性回滚），
而非检索层：GraphRAG 只读、无受治理写回路径，挡不住"写错"。

与行业无关：清单与校验都从 registry 派生，本模块不含行业词汇。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..query.oql import Aggregate, Cond, OQLQuery, OQLValidationError, Step, validate as oql_validate
from ..sdk.errors import ResolutionError
from .llm import LLMClient
from .manifest import build_manifest, render_manifest

_SYSTEM = """你是一个本体意图编译器。用户的话要么是"做一件事"(动作)，要么是"查一个东西"(查询)。
只能用下面"能力清单"里声明的动作/对象/关系/字段，禁止编造清单外的名字。
只输出一个 JSON 对象，字段：
  - kind: "action"(执行动作) | "query"(查询数据) | "clarify"(信息不足/超范围)
  - action / params: kind=action 时，所选动作名 + 参数（键只用该动作声明的参数名）
  - oql: kind=query 时，一个结构化查询对象（见下）
  - question: kind=clarify 时向用户追问的一句话
  - confidence: 数字 0~1
OQL 查询结构(oql)：
  - start: 锚点对象类型(取自清单)
  - where: 数组，锚点过滤 [{{"field":字段,"op":"eq|ne|gt|ge|lt|le|in","value":值}}]
  - steps: 数组，沿关系多跳 [{{"link_type":关系名,"direction":"out|in","where":[同上]}}]
  - select: 数组，要返回的字段名；或 aggregate: {{"func":"count|avg|sum|min|max","field":字段}}
  - limit: 整数(可省)
规则：
1. "出方案/评级/制定/派单"等执行类 → kind=action，给出 action 与 params。
2. "有哪些/查/列出/统计/多少/哪些适配"等读取类 → kind=query，给出 oql。
3. 信息不足（缺必填参数或意图不清）或超出清单能力 → kind=clarify。
不要输出 JSON 以外的任何内容。
能力清单：
{manifest}"""


@dataclass
class CompiledIntent:
    kind: str                       # action | query | clarify | reject
    action: Optional[str] = None
    params: dict = field(default_factory=dict)
    oql: Optional[OQLQuery] = None  # kind=query 时的已校验 OQL
    confidence: float = 0.0
    question: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def executable(self) -> bool:
        return self.kind == "action"

    @property
    def is_query(self) -> bool:
        return self.kind == "query"


def _parse_oql(d: dict, namespace: str) -> OQLQuery:
    def conds(raw):
        return tuple(Cond(c["field"], c["op"], c["value"]) for c in (raw or []))
    steps = tuple(
        Step(s["link_type"], s.get("direction", "out"), conds(s.get("where")))
        for s in (d.get("steps") or [])
    )
    agg = None
    if d.get("aggregate"):
        agg = Aggregate(d["aggregate"]["func"], d["aggregate"].get("field"))
    return OQLQuery(
        namespace=namespace, start=d["start"], where=conds(d.get("where")),
        steps=steps, select=tuple(d.get("select") or ()), aggregate=agg,
        limit=int(d.get("limit", 100)),
    )


class IntentCompiler:
    def __init__(self, client: LLMClient, registry, *, min_confidence: float = 0.55) -> None:
        self.client = client
        self.registry = registry
        self.min_confidence = min_confidence

    def compile(self, ontology_id: str, utterance: str, *,
                memory_text: str = "", actor_role: Optional[str] = None) -> CompiledIntent:
        manifest = build_manifest(self.registry, ontology_id)
        system = _SYSTEM.format(manifest=render_manifest(manifest))
        parts = []
        if actor_role:
            parts.append(f"用户角色：{actor_role}")
        if memory_text:
            parts.append(f"相关记忆/上下文：\n{memory_text}")
        parts.append(f"用户说：{utterance}")
        raw = self.client.complete_json(system, "\n".join(parts))

        kind = raw.get("kind")
        conf = float(raw.get("confidence", 0.0) or 0.0)
        if kind == "clarify":
            return CompiledIntent("clarify", confidence=conf, question=raw.get("question", ""), raw=raw)
        if kind == "query":
            # NL→OQL：解析 + schema 校验（防注入、落地）。校验失败即拒。
            try:
                q = _parse_oql(raw.get("oql") or {}, ontology_id)
                oql_validate(q, self.registry)
            except (KeyError, OQLValidationError) as e:
                return CompiledIntent("reject", confidence=conf, error=f"非法查询: {e}", raw=raw)
            return CompiledIntent("query", oql=q, confidence=conf, raw=raw)
        if kind != "action":
            return CompiledIntent("reject", confidence=conf, error=f"非法 kind: {kind}", raw=raw)

        action = raw.get("action") or ""
        params = dict(raw.get("params") or {})
        # 确定性校验 —— 动作存在
        try:
            adef = self.registry.get_action(ontology_id, action)
        except ResolutionError:
            return CompiledIntent("reject", confidence=conf, action=action,
                                  error=f"清单外动作: {action}", raw=raw)
        # 参数校验 —— 名⊆声明（防注入）、必填齐全
        declared = {p.name for p in adef.params}
        required = {p.name for p in adef.params if p.required}
        unknown = set(params) - declared
        if unknown:
            return CompiledIntent("reject", confidence=conf, action=action,
                                  error=f"越界参数(清单外): {sorted(unknown)}", raw=raw)
        missing = required - set(params)
        if missing:
            return CompiledIntent("clarify", confidence=conf, action=action, params=params,
                                  question=f"还需要：{sorted(missing)}", raw=raw)
        # 置信度路由（置信度总线）
        if conf < self.min_confidence:
            return CompiledIntent("clarify", confidence=conf, action=action, params=params,
                                  question="理解置信度较低，请确认你的意图", raw=raw)
        return CompiledIntent("action", action=action, params=params, confidence=conf, raw=raw)
