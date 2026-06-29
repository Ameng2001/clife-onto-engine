"""审计与 commit journal 的 SQLite 持久后端（stdlib sqlite3，零依赖）。

与内存版 `AuditStore` / `CommitJournal` **同接口**，可直接注入 ActionEngine 替换。
持久化带来两件事：① 审计/血统重启不丢（合规）；② commit journal 的 pending 条目跨进程留存，
是崩溃恢复（roll_back_pending）的依据。对应方法论 Software 3.0 的 YAML→JSONL→SQLite 演进。

与行业无关（CI 强制）。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from .audit import AuditSnapshot, RuleEvaluation
from .journal import JournalEntry


def _connect(db_path: str) -> sqlite3.Connection:
    # autocommit（isolation_level=None）+ WAL：多连接同文件时写即对其它连接可见，避免互相不可见。
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class SqliteAuditStore:
    def __init__(self, db_path: str) -> None:
        self._db = _connect(db_path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS audit "
            "(ontology_id TEXT, action TEXT, decision TEXT, doc TEXT)"
        )

    def record(self, snap: AuditSnapshot) -> None:
        self._db.execute(
            "INSERT INTO audit(ontology_id, action, decision, doc) VALUES (?,?,?,?)",
            (snap.ontology_id, snap.action, snap.decision,
             json.dumps(snap.to_dict(), ensure_ascii=False)),
        )

    def query(self, ontology_id: str) -> list[AuditSnapshot]:
        rows = self._db.execute(
            "SELECT doc FROM audit WHERE ontology_id=? ORDER BY rowid", (ontology_id,)
        ).fetchall()
        return [_audit_from_dict(json.loads(r[0])) for r in rows]

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]


class SqliteCommitJournal:
    def __init__(self, db_path: str) -> None:
        self._db = _connect(db_path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS journal "
            "(ontology_id TEXT, action TEXT, status TEXT, ops TEXT, error TEXT, ts TEXT)"
        )

    def record(self, entry: JournalEntry) -> None:
        self._db.execute(
            "INSERT INTO journal(ontology_id, action, status, ops, error, ts) VALUES (?,?,?,?,?,?)",
            (entry.ontology_id, entry.action, entry.status,
             json.dumps(list(entry.ops), ensure_ascii=False), entry.error, entry.ts),
        )

    def query(self, ontology_id: str) -> list[JournalEntry]:
        rows = self._db.execute(
            "SELECT ontology_id, action, status, ops, error, ts FROM journal "
            "WHERE ontology_id=? ORDER BY rowid", (ontology_id,)
        ).fetchall()
        return [_journal_from_row(r) for r in rows]

    def pending(self) -> list[JournalEntry]:
        rows = self._db.execute(
            "SELECT ontology_id, action, status, ops, error, ts FROM journal ORDER BY rowid"
        ).fetchall()
        entries = [_journal_from_row(r) for r in rows]
        terminal = {(e.ontology_id, e.action, e.ops) for e in entries
                    if e.status in ("committed", "compensated")}
        return [e for e in entries
                if e.status == "pending" and (e.ontology_id, e.action, e.ops) not in terminal]

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM journal").fetchone()[0]


def _audit_from_dict(d: dict) -> AuditSnapshot:
    return AuditSnapshot(
        ontology_id=d["ontology_id"], action=d["action"],
        actor_id=d["actor"]["id"], actor_role=d["actor"]["role"],
        inputs_snapshot=d["inputs_snapshot"],
        rules_evaluated=tuple(RuleEvaluation(**r) for r in d["rules_evaluated"]),
        decision=d["decision"], confidence=d["confidence"],
        evidence=tuple(d["evidence"]), schema_version=d["schema_version"], ts=d.get("ts"),
    )


def _journal_from_row(r) -> JournalEntry:
    return JournalEntry(ontology_id=r[0], action=r[1], status=r[2],
                        ops=tuple(json.loads(r[3])), error=r[4], ts=r[5])
