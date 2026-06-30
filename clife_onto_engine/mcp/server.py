"""最小 JSON-RPC (MCP) stdio 适配 —— 把 GovernedBridge 暴露为 MCP 工具。

只实现握手 + 工具发现/调用所需的最小子集（initialize / tools.list / tools.call），
不自研协议语义、不引重依赖（开源优先·薄适配）。治理逻辑全在 bridge，本模块只搬运。

工具：
  · query(utterance)                     —— 受治理读（经引擎 OQL）
  · act(action, params, actor_role?)     —— 受治理写（经 ActionEngine），仅 enable_act 时注册
"""
from __future__ import annotations

import json
import sys
from typing import Optional

from .bridge import GovernedBridge

PROTOCOL_VERSION = "2024-11-05"

_TOOL_SCHEMAS = {
    "query": {
        "name": "query",
        "description": "受治理读：一句口语 → 引擎 OQL（schema 校验/防注入）→ 结构化行。",
        "inputSchema": {"type": "object", "required": ["utterance"],
                        "properties": {"utterance": {"type": "string"}}},
    },
    "act": {
        "name": "act",
        "description": "受治理写：执行一个已声明 Action，全程经引擎 guard→写后规则→提交/确定性回滚→审计；"
                       "提交后把已提交状态反映进 UModel 读层。拒绝返回结构化 violations。",
        "inputSchema": {"type": "object", "required": ["action", "params"],
                        "properties": {"action": {"type": "string"},
                                       "params": {"type": "object"},
                                       "actor_role": {"type": "string"}}},
    },
}


def _tool_list(bridge: GovernedBridge) -> dict:
    return {"tools": [_TOOL_SCHEMAS[name] for name in bridge.tools()]}


def _tool_call(bridge: GovernedBridge, name: str, args: dict) -> dict:
    if name == "query":
        result = bridge.query(args["utterance"])
    elif name == "act":
        result = bridge.act(args["action"], args.get("params", {}),
                            actor_role=args.get("actor_role"))
    else:
        raise ValueError(f"未知工具: {name}")
    # MCP content 约定：结构化结果以 text(JSON) 承载。
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


def dispatch(bridge: GovernedBridge, msg: dict) -> Optional[dict]:
    """处理一条 JSON-RPC 请求，返回响应（通知返回 None）。纯函数 → 可单测。"""
    mid = msg.get("id")
    method = msg.get("method")
    try:
        if method == "initialize":
            res = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                   "serverInfo": {"name": "clife-onto-engine", "version": "0.1.0"}}
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            res = _tool_list(bridge)
        elif method == "tools/call":
            params = msg.get("params") or {}
            res = _tool_call(bridge, params.get("name"), params.get("arguments") or {})
        elif method == "ping":
            res = {}
        else:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": f"method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": res}
    except Exception as e:  # noqa: BLE001 (协议边界，转 JSON-RPC error)
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32000, "message": f"{type(e).__name__}: {e}"}}


def serve_stdio(bridge: GovernedBridge) -> None:  # pragma: no cover (I/O 循环)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        resp = dispatch(bridge, json.loads(line))
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
