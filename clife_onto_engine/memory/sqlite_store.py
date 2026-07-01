"""四层记忆的 SQLite 持久后端（stdlib sqlite3，零依赖）。

与内存版 `MemoryStore` **同接口**，可直接注入 `Session` 替换——记忆跨进程/重启不丢。
采用**子类 write-through**：复用父类全部四层逻辑（by_layer/淘汰/级联作废/滑动窗口），
每次变更后把受影响条目写穿 SQLite；`__init__` 从库加载已有条目。

与 trust/sqlite_store.py 同模式（WAL/autocommit，item 序列化成 JSON doc）。行业无关（CI 强制）。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Iterable

from .item import Layer, Lifecycle, MemoryItem
from .store import MemoryStore


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _to_doc(it: MemoryItem) -> dict:
    d = dict(it.__dict__)
    d["layer"] = it.layer.value
    d["lifecycle"] = it.lifecycle.value
    d["tags"] = list(it.tags)
    return d


def _from_doc(d: dict) -> MemoryItem:
    d = dict(d)
    d["layer"] = Layer(d["layer"])
    d["lifecycle"] = Lifecycle(d["lifecycle"])
    d["tags"] = tuple(d.get("tags", ()))
    return MemoryItem(**d)


class SqliteMemoryStore(MemoryStore):
    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._db = _connect(db_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS memory (id TEXT PRIMARY KEY, doc TEXT)")
        for (doc,) in self._db.execute("SELECT doc FROM memory ORDER BY rowid").fetchall():
            it = _from_doc(json.loads(doc))
            self._items[it.id] = it
            self._seq = max(self._seq, it.seq)

    def _persist(self, item: MemoryItem) -> None:
        self._db.execute(
            "INSERT INTO memory(id, doc) VALUES (?,?) "
            "ON CONFLICT(id) DO UPDATE SET doc=excluded.doc",
            (item.id, json.dumps(_to_doc(item), ensure_ascii=False)),
        )

    def _persist_all(self) -> None:
        for it in self._items.values():
            self._persist(it)

    # ---- 覆写：父类逻辑后写穿 ----
    def add(self, item: MemoryItem) -> MemoryItem:
        it = super().add(item)
        self._persist(it)
        return it

    def access(self, item_id: str) -> None:
        super().access(item_id)
        it = self._items.get(item_id)
        if it:
            self._persist(it)

    def record_action_outcome(self, item_ids: Iterable[str], success: bool) -> None:
        ids = list(item_ids)
        super().record_action_outcome(ids, success)
        for iid in ids:
            it = self._items.get(iid)
            if it:
                self._persist(it)

    def on_rule_change(self, ontology_id: str, rule_name: str) -> int:
        n = super().on_rule_change(ontology_id, rule_name)
        self._persist_all()  # 级联作废可能改多条，全量写穿（量受内存条目数界）
        return n

    def demote_stale(self, ontology_id: str, session_id: str, cold_below_hits: int = 1) -> None:
        super().demote_stale(ontology_id, session_id, cold_below_hits)
        self._persist_all()
