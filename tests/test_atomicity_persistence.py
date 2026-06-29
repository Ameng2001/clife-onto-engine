"""commit 原子性（undo-log 补偿）+ SQLite 持久层 + 崩溃恢复。"""
from __future__ import annotations

from clife_onto_engine import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.trust import (
    JournalEntry,
    SqliteAuditStore,
    SqliteCommitJournal,
    roll_back_pending,
)

NS = "grass"


class _Faulty:
    """第 N 次 put_object 抛错，模拟非事务后端中途失败。"""

    def __init__(self, inner, fail_on_put):
        self._inner, self._n, self._fail = inner, 0, fail_on_put

    def put_object(self, ot, k, d):
        self._n += 1
        if self._n == self._fail:
            raise RuntimeError("注入故障")
        return self._inner.put_object(ot, k, d)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def test_commit_failure_rolls_back_all(grass_store, contractor):
    store = _Faulty(grass_store, fail_on_put=2)        # 写第 2 个对象时炸
    eng = ActionEngine(spi.registry, store=store)
    res = eng.execute(NS, "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300},
                      contractor, ts="t")
    assert res.committed is False and res.phase == "commit"
    # 第 1 个写已被补偿删除，零残留
    assert grass_store.get_object("SeedPack", "sp_parcel_001") is None
    assert grass_store.get_object("Project", "proj_parcel_001") is None


def test_sqlite_durable_across_reopen(tmp_path, grass_store, contractor):
    db = str(tmp_path / "t.sqlite")
    eng = ActionEngine(spi.registry, store=grass_store,
                       audit=SqliteAuditStore(db), journal=SqliteCommitJournal(db))
    eng.execute(NS, "出一地一方",
                {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300}, contractor, ts="t")
    # 新连接（模拟重启）仍读得到
    assert len(SqliteAuditStore(db).query(NS)) == 1
    assert [e.status for e in SqliteCommitJournal(db).query(NS)] == ["pending", "committed"]


def test_roll_back_pending_recovers(grass_store):
    j = SqliteCommitJournalMem()
    grass_store.put_object("SeedPack", "sp_orphan", {"x": 1})
    j.record(JournalEntry(NS, "出一地一方", "pending", ("obj:SeedPack:sp_orphan",), ts="t"))
    n = roll_back_pending(j, grass_store)
    assert n == 1
    assert grass_store.get_object("SeedPack", "sp_orphan") is None
    assert j.pending() == []


class SqliteCommitJournalMem:
    """内存版 journal（避免本测试依赖临时文件），接口与 CommitJournal 一致。"""

    def __init__(self):
        from clife_onto_engine.trust import CommitJournal
        self._j = CommitJournal()

    def record(self, e):
        self._j.record(e)

    def pending(self):
        return self._j.pending()

    def query(self, ns):
        return self._j.query(ns)
