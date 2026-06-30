"""引擎 MCP 面 —— 让 MCP agent 受治理地查（query）与做（act，opt-in）。

`GovernedBridge` 是传输无关的治理核心（写只经 ActionEngine、只反映已提交状态）；
`serve_stdio` 是最小 JSON-RPC stdio 适配。与行业无关（CI 强制）。
"""
from .bridge import GovernedBridge, Reflector

__all__ = ["GovernedBridge", "Reflector", "serve_stdio"]


def serve_stdio(bridge: "GovernedBridge") -> None:  # pragma: no cover (I/O 循环)
    from .server import serve_stdio as _serve
    _serve(bridge)
