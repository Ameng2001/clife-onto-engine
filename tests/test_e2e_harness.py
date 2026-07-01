"""端到端 harness（桩模式）：整栈跑一段 施工方 会话，验 OAG 回路核心 + 审计。"""
from __future__ import annotations

from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

# 复用 harness 的真实感数据 + 脚本编译器 + 剧本
from scripts.e2e_harness import STEPS, ScriptedCompiler, seed

import plugins.grass  # noqa: F401


def _run():
    store = seed()
    s = Session(ontology_id="grass", registry=spi.registry, store=store,
                compiler=ScriptedCompiler(), actor=Actor("u1", "施工方"),
                session_id="t_e2e", schema_version="grass@0.1.0", load_knowledge=True)
    return s, [s.ask(u) for u in STEPS]


def test_full_loop_kinds():
    s, replies = _run()
    kinds = [r.kind for r in replies]
    assert kinds.count("query") == 2
    assert kinds.count("committed") == 1
    assert kinds.count("rejected") == 2      # 非乡土 + 跨区域用错草种
    assert kinds.count("clarify") == 1


def test_governance_caught_with_suggestion():
    s, replies = _run()
    rej = [r for r in replies if r.kind == "rejected"]
    assert all(any(v.rule == "乡土合规" for v in r.violations) for r in rej)
    assert all(r.violations[0].suggestion for r in rej)     # 拒绝带可操作建议


def test_audit_trail():
    s, replies = _run()
    au = s.engine.audit.query("grass")
    decisions = {a.decision for a in au}
    assert "committed" in decisions and "rejected" in decisions


def test_knowledge_grounded_in_session():
    from clife_onto_engine.memory import Layer
    s, _ = _run()
    # load_knowledge=True → BACKGROUND 层有附着知识（供 LLM 推理）
    assert s.memory.by_layer(Layer.BACKGROUND, "grass", "t_e2e")
