"""冒烟：commit-path 原子性 —— 后端写入中途失败，确定性补偿回滚到提交前。

注入一个"写第 2 个对象时故障"的后端，跑 出一地一方（依次写 SeedPack、Project）。
期望：第 2 次写失败 → undo-log 撤销已写的 SeedPack → 图库零残留；返回 phase=commit 的
结构化拒绝；journal 记 pending→compensated。

运行：python scripts/smoke_atomic.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi

from plugins.grass import seed_reference_data

NS = "grass"


class FaultyStore:
    """包装真实后端，在第 N 次 put_object 时抛错（模拟非事务后端中途失败）。"""

    def __init__(self, inner, fail_on_put: int) -> None:
        self._inner = inner
        self._puts = 0
        self._fail_on = fail_on_put

    def put_object(self, object_type, key, data):
        self._puts += 1
        if self._puts == self._fail_on:
            raise RuntimeError(f"注入故障：后端写第 {self._fail_on} 个对象失败")
        return self._inner.put_object(object_type, key, data)

    def __getattr__(self, name):
        return getattr(self._inner, name)  # 其余方法透传


def main() -> None:
    base = InMemoryStore()
    seed_reference_data(base)
    store = FaultyStore(base, fail_on_put=2)   # 第 2 个对象（Project）写入时炸
    engine = ActionEngine(spi.registry, store=store)
    actor = Actor("u1", "施工方")

    print("== 合规方案，但后端在写第 2 个对象时故障 → 期望整体回滚 ==")
    res = engine.execute(NS, "出一地一方",
                         {"site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300},
                         actor, schema_version="grass@0.1.0", ts="2026-06-29T09:00:00")

    print(f"  committed={res.committed} phase={getattr(res, 'phase', None)}")
    for v in getattr(res, "violations", ()):
        print(f"    ✗ {v.rule}: {v.message} | 建议: {v.suggestion}")

    # 关键断言：第 1 个对象（SeedPack）已被补偿删除，图库零残留
    sp = base.get_object("SeedPack", "sp_parcel_001")
    pj = base.get_object("Project", "proj_parcel_001")
    print(f"  图库残留 SeedPack={sp} Project={pj}")

    print("== commit 日志（WAL）==")
    for e in engine.journal.query(NS):
        print(f"    {e.status:11} ops={e.ops} err={e.error[:30]}")

    ok = (not res.committed and getattr(res, "phase", None) == "commit"
          and sp is None and pj is None
          and any(e.status == "compensated" for e in engine.journal.query(NS)))
    print(f"== {'OK：commit 中途失败已 all-or-nothing 回滚，图库零残留' if ok else '失败：断言不符'} ==")


if __name__ == "__main__":
    main()
