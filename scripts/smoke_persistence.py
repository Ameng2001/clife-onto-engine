"""冒烟：审计/journal 持久层（SQLite）+ 崩溃恢复。

A. 用 SQLite 审计/journal 跑一个 commit，**新建 store 实例指向同一 db**（模拟重启）→ 审计/journal 不丢。
B. 模拟"进程在 flush 中途崩溃"：手工写入一条孤儿 pending + 其对象进图库，
   重启后 roll_back_pending → 对象被删、补记 compensated。

运行：python scripts/smoke_persistence.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi
from clife_onto_engine.trust import (
    JournalEntry,
    SqliteAuditStore,
    SqliteCommitJournal,
    roll_back_pending,
)

from plugins.grass import seed_reference_data

NS = "grass"
ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "build" / "persistence_demo.sqlite"


def main() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    for sidecar in (DB, DB.with_name(DB.name + "-wal"), DB.with_name(DB.name + "-shm")):
        if sidecar.exists():
            sidecar.unlink()  # 连 WAL 旁文件一起清，干净开始

    graph = InMemoryStore()
    seed_reference_data(graph)

    print("== A. SQLite 审计/journal 跑一个 commit ==")
    engine = ActionEngine(spi.registry, store=graph,
                          audit=SqliteAuditStore(str(DB)), journal=SqliteCommitJournal(str(DB)))
    res = engine.execute(NS, "出一地一方",
                         {"site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300},
                         Actor("u1", "施工方"), schema_version="grass@0.1.0", ts="2026-06-29T10:00:00")
    print(f"  committed={res.committed}")

    print("== 模拟重启：新建 store 实例指向同一 db 文件 ==")
    audit2 = SqliteAuditStore(str(DB))
    journal2 = SqliteCommitJournal(str(DB))
    print(f"  审计条数={len(audit2)}（重启后仍在）；动作={[a.action for a in audit2.query(NS)]}")
    print(f"  journal 条数={len(journal2)}；状态={[e.status for e in journal2.query(NS)]}")

    print("== B. 模拟崩溃中途：手工写孤儿 pending + 对象进图库 ==")
    graph.put_object("SeedPack", "sp_orphan", {"site_id": "orphan"})
    graph.put_object("Project", "proj_orphan", {"site_id": "orphan"})
    journal2.record(JournalEntry(NS, "出一地一方", "pending",
                                 ("obj:SeedPack:sp_orphan", "obj:Project:proj_orphan"),
                                 ts="2026-06-29T10:05:00"))
    print(f"  崩溃前图库残留: SeedPack={graph.get_object('SeedPack','sp_orphan')}")
    print(f"  pending 待恢复: {[ (e.action, e.ops) for e in journal2.pending() ]}")

    print("== 重启后执行崩溃恢复 roll_back_pending ==")
    n = roll_back_pending(journal2, graph)
    print(f"  回滚 {n} 个孤儿动作")
    print(f"  恢复后图库: SeedPack={graph.get_object('SeedPack','sp_orphan')} "
          f"Project={graph.get_object('Project','proj_orphan')}")
    print(f"  pending 清空: {journal2.pending() == []}")

    ok = (res.committed and len(audit2) == 1 and n == 1
          and graph.get_object("SeedPack", "sp_orphan") is None
          and journal2.pending() == [])
    print(f"== {'OK：持久化跨重启不丢 + 崩溃恢复回滚孤儿提交' if ok else '失败：断言不符'} ==")


if __name__ == "__main__":
    main()
