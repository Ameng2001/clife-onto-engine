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

from ..sdk.errors import ResolutionError
from .llm import LLMClient
from .manifest import build_manifest, render_manifest

_SYSTEM = """你是一个本体动作意图编译器。只能从下面这份"能力清单"里选择动作，禁止编造清单外的动作或参数名。
只输出一个 JSON 对象，字段：
  - kind: "action" 或 "clarify"
  - action: 字符串，kind=action 时所选动作名（必须取自清单）
  - params: 对象，动作参数，键只用该动作声明的参数名
  - question: 字符串，kind=clarify 时向用户追问的一句话
  - confidence: 数字 0~1，对本次理解的置信度
规则：
1. 用户意图能明确映射到某动作且必填参数齐全时，kind=action，给出 action 与 params。
2. 信息不足（缺必填参数或意图不清）时，kind=clarify，给出一句追问 question。
3. 用户诉求超出清单能力范围时，也用 kind=clarify 说明无法处理。
不要输出 JSON 以外的任何内容。
能力清单：
{manifest}"""


@dataclass
class CompiledIntent:
    kind: str                       # action | clarify | reject
    action: Optional[str] = None
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    question: str = ""
    error: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def executable(self) -> bool:
        return self.kind == "action"


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
