"""Session —— 统一应用门面：一次 ask(口语) 跑完整回路。

把散落的能力收口成一个入口：记忆接地 → 意图编译路由 →（查：执行 OQL ／ 做：走 Action 引擎，
guard/写后规则/回滚/审计）→ 回写记忆 → 返回结构化结果。与行业无关（CI 强制）。

    session = Session(ontology_id="<industry>", registry=spi.registry, store=store,
                      compiler=IntentCompiler(client, spi.registry), actor=Actor("u1", "<role>"))
    reply = session.ask("<一句口语：查询或执行>")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .intent.compiler import IntentCompiler
from .kernel import ActionEngine
from .memory import Layer, MemoryItem, MemoryStore, assemble
from .query import QueryView
from .query.oql import execute as oql_execute
from .sdk.context import Actor


@dataclass
class Reply:
    kind: str                       # query | committed | rejected | clarify | error
    confidence: float = 0.0
    # query
    rows: Optional[list] = None
    cost: Optional[dict] = None
    oql: object = None
    # action
    written: tuple = ()
    violations: tuple = ()
    # clarify / error / advise
    question: str = ""
    answer: str = ""                # kind=advise：知识接地的只读建议
    error: str = ""

    def summary(self) -> str:
        if self.kind == "query":
            return f"[查询] {len(self.rows or [])} 行 · 成本{self.cost} · {self.rows}"
        if self.kind == "committed":
            return f"[已执行] 写入 {list(self.written)}"
        if self.kind == "rejected":
            return f"[被拒] 违反 {[v.rule for v in self.violations]}：" + \
                   "；".join(f"{v.message}" for v in self.violations)
        if self.kind == "advise":
            return f"[建议] {self.answer}"
        if self.kind == "clarify":
            return f"[澄清] {self.question}"
        return f"[错误] {self.error}"


class Session:
    def __init__(self, *, ontology_id: str, registry, store, compiler: IntentCompiler,
                 actor: Actor, memory: Optional[MemoryStore] = None, session_id: str = "s1",
                 engine: Optional[ActionEngine] = None, schema_version: str = "",
                 load_knowledge: bool = False) -> None:
        self.ontology_id = ontology_id
        self.registry = registry
        self.store = store
        self.compiler = compiler
        self.actor = actor
        self.memory = memory if memory is not None else MemoryStore()
        self.session_id = session_id
        self.engine = engine if engine is not None else ActionEngine(registry, store=store)
        self.schema_version = schema_version
        self._n = 0
        # 附着知识喂进 BACKGROUND 层：ask 装配时按相关性注入 LLM，供领域知识推理（默认关，向后兼容）。
        if load_knowledge:
            from .knowledge import load_into_memory
            load_into_memory(registry, self.memory, ontology_id, session_id)

    def ask(self, utterance: str, *, ts: Optional[str] = None) -> Reply:
        # 1. 记忆接地：装配本会话 CONTEXT/CRITICAL 喂给编译器
        mem = assemble(self.memory, self.ontology_id, self.session_id, self._keywords(utterance))
        self._remember(Layer.CONTEXT, f"用户问：{utterance}", tags=("utterance",), source="user")

        # 2. 意图编译（路由 做/查/澄清）
        ci = self.compiler.compile(self.ontology_id, utterance,
                                   memory_text=mem.text, actor_role=self.actor.role)

        # 3a. 查：执行 OQL
        if ci.is_query:
            r = oql_execute(ci.oql, QueryView(self.store, []), self.registry)
            self._remember(Layer.CONTEXT, f"查询返回 {len(r.rows)} 行", tags=("result",), source="action_result")
            return Reply("query", ci.confidence, rows=r.rows, cost=r.cost, oql=ci.oql)

        # 3b. 做：走 Action 引擎（guard/写后规则/回滚/审计）
        if ci.executable:
            res = self.engine.execute(self.ontology_id, ci.action, ci.params, self.actor,
                                      schema_version=self.schema_version, ts=ts)
            self._remember(Layer.CONTEXT, f"动作 {ci.action} committed={res.committed}",
                           tags=("result",), source="action_result")
            if res.committed:
                return Reply("committed", ci.confidence, written=getattr(res, "written", ()))
            return Reply("rejected", ci.confidence, violations=tuple(getattr(res, "violations", ())))

        # 3c. 咨询：知识接地的只读建议（不进 Action 引擎、不写库、不越权）
        if ci.kind == "advise":
            self._remember(Layer.CONTEXT, f"建议：{ci.answer}", tags=("advise",), source="advise")
            return Reply("advise", ci.confidence, answer=ci.answer)

        # 3d. 澄清 / 错误
        if ci.kind == "clarify":
            return Reply("clarify", ci.confidence, question=ci.question)
        return Reply("error", ci.confidence, error=ci.error)

    # ---- 内部 ----
    def _keywords(self, utterance: str) -> set:
        cleaned = utterance.replace("？", " ").replace("?", " ").replace("，", " ").replace("。", " ")
        return {w for w in cleaned.split() if w}

    def _remember(self, layer: Layer, content: str, *, tags=(), source="") -> None:
        self._n += 1
        self.memory.add(MemoryItem(
            id=f"{self.session_id}:{self._n}", ontology_id=self.ontology_id,
            session_id=self.session_id, layer=layer, content=content,
            tags=tuple(tags), source=source,
        ))
