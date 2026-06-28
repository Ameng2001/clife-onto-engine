"""意图×编排 桥接 —— 把意图编译器接成多智能体管线里的 Agent（通用，行业无关）。

产品回路：NL --intent(编译,带记忆上下文)--> CONTEXT 记忆 --act(执行)--> 真 Action 引擎。

要点：Action 引擎自带 guard/写后规则/回滚 = 确定性验证器，故无需单独 SimAgent；
intent 只负责"在能力清单内把话翻成结构化意图"，校验与执行由引擎兜底。
"""
from __future__ import annotations

import json
from typing import Optional

from ..memory import Layer
from ..orchestration import AgentResult, AgentSpec
from .compiler import IntentCompiler


def _find_tag(ctx, tag: str) -> Optional[dict]:
    for it in ctx.recall({tag}).items:
        if tag in it.tags:
            return json.loads(it.content)
    return None


def make_intent_agent(compiler: IntentCompiler, ontology_id: str, *,
                      name: str = "intent",
                      recall_keywords: tuple = ("intent", "约束", "constraint")) -> AgentSpec:
    """读 CONTEXT+CRITICAL 做记忆接地，编译 NL→结构化意图，写回 CONTEXT。"""

    def fn(ctx) -> AgentResult:
        utterance = ctx.intent["utterance"]
        role = ctx.intent.get("actor_role")
        mem = ctx.recall(set(recall_keywords))            # 记忆接地（含 CRITICAL 约束）
        ci = compiler.compile(ontology_id, utterance, memory_text=mem.text, actor_role=role)
        payload = {"kind": ci.kind, "action": ci.action, "params": ci.params,
                   "question": ci.question, "confidence": ci.confidence, "error": ci.error}
        ctx.remember(Layer.CONTEXT, json.dumps(payload, ensure_ascii=False),
                     tags=("intent",), source="user", confidence=ci.confidence)
        return AgentResult("done" if ci.executable else f"need:{ci.kind}", payload)

    return AgentSpec(name, frozenset({Layer.CONTEXT, Layer.CRITICAL}),
                     frozenset({Layer.CONTEXT}), fn)


def make_action_agent(engine, ontology_id: str, *, actor, name: str = "act",
                      schema_version: str = "", ts: Optional[str] = None,
                      depends_on: tuple = ("intent",)) -> AgentSpec:
    """读 CONTEXT 里的已编译意图，可执行则交真引擎执行；否则跳过并带回澄清。"""

    def fn(ctx) -> AgentResult:
        intent = _find_tag(ctx, "intent")
        if not intent or intent.get("kind") != "action":
            reason = (intent or {}).get("question") or (intent or {}).get("error") or "无可执行意图"
            ctx.remember(Layer.CONTEXT, json.dumps({"skipped": True, "reason": reason}, ensure_ascii=False),
                         tags=("action_result",), source="action_result")
            return AgentResult("skipped", {"reason": reason})
        res = engine.execute(ontology_id, intent["action"], intent["params"], actor,
                             schema_version=schema_version, ts=ts)
        outcome = {"committed": res.committed,
                   "detail": getattr(res, "written", None) or
                             [v.rule for v in getattr(res, "violations", ())]}
        ctx.remember(Layer.CONTEXT, json.dumps(outcome, ensure_ascii=False),
                     tags=("action_result",), source="action_result")
        return AgentResult("done", outcome)

    return AgentSpec(name, frozenset({Layer.CONTEXT}), frozenset({Layer.CONTEXT}),
                     fn, depends_on=depends_on)
