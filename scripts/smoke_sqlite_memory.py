"""记忆持久层 smoke —— 四层记忆跨重启不丢（write-through SQLite）。全离线。"""
from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.memory import Layer, MemoryItem
from clife_onto_engine.memory.sqlite_store import SqliteMemoryStore


def _item(i, layer=Layer.CONTEXT, hits=0):
    return MemoryItem(id=i, ontology_id="ont", session_id="s1", layer=layer,
                      content=f"记忆内容 {i}", hit_count=hits)


def main() -> int:
    fails = 0
    with tempfile.TemporaryDirectory() as tmp:
        db = str(pathlib.Path(tmp) / "mem.db")

        m1 = SqliteMemoryStore(db)
        m1.add(_item("a", Layer.CRITICAL))
        m1.add(_item("b", Layer.CONTEXT))
        m1.access("b")  # hit_count → 1

        # 重开同库 → 恢复
        m2 = SqliteMemoryStore(db)
        ok = (m2.get("a") is not None and m2.get("b") is not None
              and m2.get("b").hit_count == 1)
        print(f"== 跨重启恢复 + hit_count 持久：{'✓' if ok else '✗'} "
              f"(b.hit_count={m2.get('b').hit_count if m2.get('b') else None}) ==")
        fails += not ok

        # by_layer 继承父类逻辑
        crit = m2.by_layer(Layer.CRITICAL, "ont", "s1")
        ok2 = any(it.id == "a" for it in crit)
        print(f"== by_layer 继承照常：{'✓' if ok2 else '✗'} ==")
        fails += not ok2

        # on_rule_change 级联作废持久
        m2.add(MemoryItem(id="r", ontology_id="ont", session_id="s1", layer=Layer.RULE,
                          content="规则记忆", bound_entity="某规则"))
        m2.on_rule_change("ont", "某规则")
        m3 = SqliteMemoryStore(db)
        from clife_onto_engine.memory.item import Lifecycle
        ok3 = m3.get("r").lifecycle == Lifecycle.DEPRECATED
        print(f"== 级联作废持久：{'✓' if ok3 else '✗'} ==")
        fails += not ok3

    if fails:
        print(f"\n✗ 记忆持久层 smoke 失败（{fails}）"); return 1
    print("\n✓ 记忆持久层 smoke 全通过：跨重启不丢 · 变更写穿 · 四层逻辑复用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
