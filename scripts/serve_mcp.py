"""启动引擎 MCP server（stdio）—— 让 MCP agent 受治理地查（query）与做（act）。

环境变量：
  ONTO=grass                 本体（默认 grass）
  ONTO_ENABLE_ACT=1          开启受治理写工具 act（默认关；opt-in，映射 HIL/治理纪律）
  UMODEL_URL=http://host:8081  提交后把已提交状态反映进 UModel 读层（不设则只做不反映）
  ONTO_ACTOR_ROLE=施工方      actor 角色（经引擎 guard 校验）
LLM 凭据（query 路径用）从 env/llm.local.json 读取；未配置时 act 仍可用、query 返回错误。

运行（被 MCP 客户端作为 stdio 子进程拉起；也可手测）：
  ONTO_ENABLE_ACT=1 UMODEL_URL=http://localhost:8081 python scripts/serve_mcp.py
"""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.mcp import GovernedBridge, Reflector, serve_stdio
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi

from repl import seed  # 复用 REPL 的 demo 数据 seed

_DEFAULT_ROLE = {"grass": "施工方", "chili": "种植户"}
_TRUTHY = {"1", "true", "yes", "on"}


class _LazyCompiler:
    """惰性意图编译器：未配置 LLM 时不阻断 act；query 首次调用才构建（失败则结构化报错）。"""

    def __init__(self) -> None:
        self._real = None

    def compile(self, *args, **kwargs):
        if self._real is None:
            from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
            client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
            self._real = IntentCompiler(client, spi.registry)
        return self._real.compile(*args, **kwargs)


def build_bridge() -> GovernedBridge:
    ont = os.getenv("ONTO", "grass")
    enable_act = os.getenv("ONTO_ENABLE_ACT", "").lower() in _TRUTHY
    umodel_url = os.getenv("UMODEL_URL", "").strip()
    role = os.getenv("ONTO_ACTOR_ROLE", _DEFAULT_ROLE.get(ont, "用户"))

    store = InMemoryStore()
    seed(store, ont)
    reflector = Reflector(umodel_url, ont) if umodel_url else None
    return GovernedBridge(
        ontology_id=ont, registry=spi.registry, store=store,
        compiler=_LazyCompiler(), actor=Actor("u1", role),
        engine=ActionEngine(spi.registry, store=store),
        reflector=reflector, enable_act=enable_act,
    )


def main() -> None:
    bridge = build_bridge()
    print(f"[mcp] ontology={bridge.ontology_id} tools={bridge.tools()} "
          f"reflect={'on' if bridge.reflector else 'off'}", file=sys.stderr, flush=True)
    serve_stdio(bridge)


if __name__ == "__main__":
    main()
