"""记忆 token 估算：CJK-aware 零依赖启发式（英文不再高估）+ assemble 可注入真 tokenizer。"""
from __future__ import annotations

from clife_onto_engine.memory import Layer, MemoryItem, MemoryStore, assemble
from clife_onto_engine.memory.retrieval import estimate_tokens

NS, SID = "grass", "s"


def test_cjk_one_per_char_ascii_not_overcounted():
    assert estimate_tokens("退化诊断") == 4               # 中文 ~1 token/字
    assert estimate_tokens("hello world") == 3            # 11 字符 → ceil(11/4)=3，不再 11
    assert estimate_tokens("") == 0
    # 混合：中文按字 + 英文按 ~4char/token
    assert estimate_tokens("盐碱地 pH7") == 3 + (4 + 3) // 4  # 3 中文 + "pH7"(含空格4字符)→1


def test_ascii_no_longer_over_dropped_vs_naive():
    # 同一段英文，改进后估算远小于"每字符 1 token"
    text = "restoration plan for saline alkali land"   # 39 字符
    assert estimate_tokens(text) < len(text) / 3        # ~10 而非 39


def test_assemble_accepts_injected_tokenizer():
    s = MemoryStore()
    s.add(MemoryItem(id=f"{SID}:0", ontology_id=NS, session_id=SID, layer=Layer.RULE, content="规则一"))
    s.add(MemoryItem(id=f"{SID}:1", ontology_id=NS, session_id=SID, layer=Layer.RULE, content="规则二"))
    seen = []

    def fake_tok(t):
        seen.append(t); return 1000                      # 每项 1000 token

    ctx = assemble(s, NS, SID, set(), budget={Layer.RULE: 1500}, token_fn=fake_tok)
    assert seen                                          # 注入的 tokenizer 被调用
    assert ctx.report[Layer.RULE].dropped >= 1           # 每项 1000、预算 1500 → 只容 1 项
