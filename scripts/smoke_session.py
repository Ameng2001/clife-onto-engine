"""冒烟：Session 统一门面（真 Qwen）—— 一句口语跑完整回路，做/查/澄清/回滚都从一个入口出。

验证 Session.ask 把"意图编译路由 → 查 OQL / 做 Action → 记忆/审计"组合成一次调用。

前置：llm.local.json + pip install openai
运行：python scripts/smoke_session.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.memory import Layer

from repl import build_session  # 复用 REPL 的会话构建（含 demo 数据 seed）

NS = "grass"


def main() -> None:
    session = build_session(NS)
    print(f"模型: {session.compiler.client.model}\n")

    cases = [
        ("查", "巴彦淖尔有哪些地块？"),
        ("查·多跳", "parcel_001 这块地能用哪些修复方法？"),
        ("做·合规", "给 parcel_001 出一地一方，用碱茅和披碱草，预算300"),
        ("做·非乡土→引擎回滚", "给 parcel_001 出方案，用紫花苜蓿，预算300"),
        ("澄清·缺参", "帮我修复一下草场"),
    ]
    kinds = []
    for tag, utt in cases:
        reply = session.ask(utt, ts="2026-06-29T12:00:00")
        kinds.append(reply.kind)
        print(f"[{tag}]「{utt}」")
        print(f"   {reply.summary()}\n")

    mem_n = len(session.memory.by_layer(Layer.CONTEXT, NS, session.session_id))
    audit_n = len(session.engine.audit.query(NS))
    print(f"== 一个入口跑通：CONTEXT 记忆 {mem_n} 条，审计 {audit_n} 条 ==")
    ok = (kinds[0] == "query" and kinds[1] == "query"
          and kinds[2] == "committed" and kinds[3] == "rejected" and kinds[4] == "clarify")
    print(f"== {'OK：做/查/澄清/回滚全部从 Session 一个入口正确路由' if ok else '失败：路由不符 ' + str(kinds)} ==")


if __name__ == "__main__":
    main()
