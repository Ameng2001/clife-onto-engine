"""意图编译内核 —— NL → 受约束、可校验的结构化意图。与行业无关。"""
from __future__ import annotations

from .agents import make_action_agent, make_intent_agent
from .compiler import CompiledIntent, IntentCompiler
from .llm import LLMClient, OpenAICompatibleClient
from .manifest import build_manifest, render_manifest

__all__ = [
    "IntentCompiler", "CompiledIntent",
    "LLMClient", "OpenAICompatibleClient",
    "build_manifest", "render_manifest",
    "make_intent_agent", "make_action_agent",
]
