"""记忆持久层：跨重启恢复、变更写穿、四层逻辑复用。"""
from __future__ import annotations

from clife_onto_engine.memory import Layer, MemoryItem
from clife_onto_engine.memory.item import Lifecycle
from clife_onto_engine.memory.sqlite_store import SqliteMemoryStore


def _it(i, layer=Layer.CONTEXT, **kw):
    return MemoryItem(id=i, ontology_id="ont", session_id="s1", layer=layer,
                      content=f"c{i}", **kw)


def test_persists_across_reopen(tmp_path):
    db = str(tmp_path / "m.db")
    m = SqliteMemoryStore(db)
    m.add(_it("a", Layer.CRITICAL))
    m.add(_it("b"))
    m2 = SqliteMemoryStore(db)
    assert m2.get("a") is not None and m2.get("b") is not None


def test_access_hit_count_persisted(tmp_path):
    db = str(tmp_path / "m.db")
    m = SqliteMemoryStore(db); m.add(_it("b"))
    m.access("b"); m.access("b")
    assert SqliteMemoryStore(db).get("b").hit_count == 2


def test_by_layer_inherited(tmp_path):
    m = SqliteMemoryStore(str(tmp_path / "m.db"))
    m.add(_it("a", Layer.CRITICAL))
    assert any(it.id == "a" for it in m.by_layer(Layer.CRITICAL, "ont", "s1"))


def test_rule_change_cascade_persisted(tmp_path):
    db = str(tmp_path / "m.db")
    m = SqliteMemoryStore(db)
    m.add(_it("r", Layer.RULE, bound_entity="规则X"))
    n = m.on_rule_change("ont", "规则X")
    assert n == 1
    assert SqliteMemoryStore(db).get("r").lifecycle == Lifecycle.DEPRECATED


def test_record_outcome_failure_persisted(tmp_path):
    db = str(tmp_path / "m.db")
    m = SqliteMemoryStore(db)
    m.add(_it("x", confidence=1.0))
    m.record_action_outcome(["x"], success=False)
    assert SqliteMemoryStore(db).get("x").confidence < 1.0


def test_seq_restored(tmp_path):
    db = str(tmp_path / "m.db")
    m = SqliteMemoryStore(db); m.add(_it("a")); m.add(_it("b"))
    m2 = SqliteMemoryStore(db); m2.add(_it("c"))
    assert m2.get("c").seq > m2.get("b").seq          # seq 从库恢复后继续单调
