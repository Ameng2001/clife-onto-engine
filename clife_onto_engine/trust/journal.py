"""提交日志（WAL 雏形）—— 记录提交期的 pending → committed / compensated。

用途：
  - 同步失败（后端拒写某 op）由引擎 undo-log **当场补偿回滚**（确定性、all-or-nothing）。
  - 进程在 flush 中途崩溃则留下 `pending` 条目；恢复程序据此回滚/前滚（未来钩子）。

骨架用内存 append-only；落地换持久后端（同接口）即获崩溃恢复能力。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class JournalEntry:
    ontology_id: str
    action: str
    status: str               # pending | committed | compensated
    ops: tuple[str, ...]      # 形如 "obj:SeedPack:sp_x" / "link:treated_by:a->b"
    error: str = ""
    ts: Optional[str] = None


class CommitJournal:
    def __init__(self) -> None:
        self._entries: list[JournalEntry] = []

    def record(self, entry: JournalEntry) -> None:
        self._entries.append(entry)

    def query(self, ontology_id: str) -> list[JournalEntry]:
        return [e for e in self._entries if e.ontology_id == ontology_id]

    def pending(self) -> list[JournalEntry]:
        """未见终态（committed/compensated）的 pending 条目 —— 崩溃恢复的入口。"""
        seen_terminal = {
            (e.ontology_id, e.action, e.ops) for e in self._entries
            if e.status in ("committed", "compensated")
        }
        return [e for e in self._entries
                if e.status == "pending" and (e.ontology_id, e.action, e.ops) not in seen_terminal]

    def __len__(self) -> int:
        return len(self._entries)


def roll_back_pending(journal, store) -> int:
    """崩溃恢复：扫描 journal 的 pending（进程中途崩溃留下的孤儿提交），把其涉及的对象删除，
    回滚到提交前，并补记 compensated 终态。delete 幂等，无论该 op 当时写没写成都安全。

    返回回滚的 pending 动作数。对象删除（NebulaGraph DELETE VERTEX ... WITH EDGE）连带清边；
    link-only 动作为最少见情形，按对象端点清理兜底。
    """
    n = 0
    for e in journal.pending():
        for label in e.ops:
            parts = label.split(":")
            if parts[0] == "obj" and len(parts) >= 3:
                object_type, key = parts[1], ":".join(parts[2:])
                try:
                    store.delete_object(object_type, key)
                except Exception:
                    pass  # 尽力而为
        journal.record(JournalEntry(e.ontology_id, e.action, "compensated", e.ops,
                                    error="recovered-on-restart", ts=e.ts))
        n += 1
    return n
