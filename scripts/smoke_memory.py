"""冒烟：记忆四层 —— 分类 / token 预算装配（CRITICAL 永驻）/ 淘汰（衰减+级联）。

运行：  python scripts/smoke_memory.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.memory import Layer, MemoryItem, MemoryStore, assemble, classify

NS, SID = "grass", "sess1"


def _add(store, content, *, source="", kind=None, bound="", compressed=""):
    layer = classify(content, source=source, bound_entity_kind=kind)
    item = MemoryItem(id=f"{SID}:{store._seq+1}", ontology_id=NS, session_id=SID,
                      layer=layer, content=content, compressed=compressed,
                      source=source, bound_entity=bound)
    store.add(item)
    print(f"  分类 → [{layer.value:10}] {content}")
    return item


def main() -> None:
    store = MemoryStore()
    print("== 三维分类（动词/来源/绑定实体）==")
    _add(store, "该地块为禁牧区，不得放牧")                                  # 不得 → CRITICAL
    r1 = _add(store, "乡土合规：种子包草种须在名录内", source="schema",
              kind="Rule", bound="乡土合规", compressed="乡土合规(名录内)")   # Rule → RULE
    _add(store, "建议优先选用本地耐盐碱草种")                                 # 建议 → RULE
    _add(store, "用户想修复 parcel_001，预算 300", source="user")           # user → CONTEXT
    _add(store, "上次出方案被拒：含非乡土草种", kind="action_result")        # → CONTEXT
    _add(store, "盐碱地通常 pH 偏高、表层易盐渍")                             # → BACKGROUND

    print("\n== token 预算装配（故意调小预算看丢弃；CRITICAL 永驻）==")
    tight = {Layer.CRITICAL: 200, Layer.RULE: 18, Layer.CONTEXT: 16, Layer.BACKGROUND: 8}
    ctx = assemble(store, NS, SID, {"乡土", "parcel_001"}, budget=tight)
    for layer, rep in ctx.report.items():
        print(f"  {layer.value:10} 预算={rep.budget:3} 用={rep.used:3} 入选={rep.included} 丢弃={rep.dropped}")
    print(f"  装配文本（CRITICAL 置顶）:\n    " + ctx.text.replace("\n", "\n    "))
    print(f"  总 tokens={ctx.total_tokens}")

    print("\n== 淘汰①：置信度衰减（操作连续失败回流）==")
    for _ in range(4):
        store.record_action_outcome([r1.id], success=False)
    print(f"  规则记忆 confidence={store.get(r1.id).confidence} lifecycle={store.get(r1.id).lifecycle.value}")

    print("== 淘汰②：规则变更级联（乡土合规 改版 → 旧记忆作废）==")
    # 先放一条仍存活、绑定同规则的记忆
    store.add(MemoryItem(id=f"{SID}:x", ontology_id=NS, session_id=SID, layer=Layer.RULE,
                         content="乡土合规旧口径", bound_entity="乡土合规"))
    n = store.on_rule_change(NS, "乡土合规")
    print(f"  级联作废 {n} 条绑定『乡土合规』的记忆")

    alive_rule = store.by_layer(Layer.RULE, NS, SID)
    print(f"  RULE 层存活记忆数={len(alive_rule)}（已作废的不再装配）")


if __name__ == "__main__":
    main()
