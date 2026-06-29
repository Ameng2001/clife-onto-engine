"""四层记忆：三维分类、token 预算装配（CRITICAL 永驻）、淘汰（衰减/级联）。"""
from __future__ import annotations

from clife_onto_engine.memory import Layer, MemoryItem, MemoryStore, assemble, classify

NS, SID = "grass", "s1"


def test_classify_three_dims():
    assert classify("该地块不得放牧") == Layer.CRITICAL              # 动词
    assert classify("用户想修复", source="user") == Layer.CONTEXT    # 来源
    assert classify("某规则", bound_entity_kind="Rule") == Layer.RULE  # 绑定实体
    assert classify("一般背景知识") == Layer.BACKGROUND


def _add(store, layer, content, **kw):
    store.add(MemoryItem(id=f"{SID}:{len(store._items)}", ontology_id=NS, session_id=SID,
                         layer=layer, content=content, **kw))


def test_budget_critical_always_in():
    s = MemoryStore()
    _add(s, Layer.CRITICAL, "硬约束A")
    _add(s, Layer.RULE, "规则一" * 5)
    _add(s, Layer.RULE, "规则二" * 5)
    tight = {Layer.CRITICAL: 50, Layer.RULE: 8, Layer.CONTEXT: 8, Layer.BACKGROUND: 4}
    ctx = assemble(s, NS, SID, set(), budget=tight)
    texts = [it.text() for it in ctx.items]
    assert "硬约束A" in texts                       # CRITICAL 必在
    assert ctx.report[Layer.RULE].dropped >= 1       # RULE 超预算有丢弃
    assert ctx.items[0].layer == Layer.CRITICAL      # 置顶


def test_confidence_decay_deprecates():
    s = MemoryStore()
    it = MemoryItem(id="x", ontology_id=NS, session_id=SID, layer=Layer.RULE, content="r")
    s.add(it)
    for _ in range(4):
        s.record_action_outcome([it.id], success=False)
    assert s.get("x").confidence < 0.3
    assert not s.get("x").alive                       # 已 deprecated


def test_rule_change_cascade():
    s = MemoryStore()
    s.add(MemoryItem(id="r1", ontology_id=NS, session_id=SID, layer=Layer.RULE,
                     content="旧口径", bound_entity="乡土合规"))
    n = s.on_rule_change(NS, "乡土合规")
    assert n == 1 and len(s.by_layer(Layer.RULE, NS, SID)) == 0
