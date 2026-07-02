"""Phase 1 · 6 子图贯通性自检 —— 断言每个子图的对象/关系都已注册，且关系端点自洽。

运行：python scripts/smoke_subgraphs.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import plugins.grass  # noqa: F401
from clife_onto_engine.sdk import spi
from plugins.grass.subgraphs import SUBGRAPHS

NS = "grass"


def main() -> int:
    r = spi.registry
    objs = {n for (ns, n) in r.objects if ns == NS}
    links = {n for (ns, n) in r.links if ns == NS}
    fails = 0

    print(f"== 6 子图贯通性自检（对象 {len(objs)} · 关系 {len(links)}）==")
    for name, sg in SUBGRAPHS.items():
        miss_o = [o for o in sg["objects"] if o not in objs]
        miss_l = [l for l in sg["links"] if l not in links]
        ok = not miss_o and not miss_l
        fails += not ok
        mark = "✓" if ok else "✗"
        detail = "" if ok else f"  缺对象{miss_o} 缺关系{miss_l}"
        print(f"  {mark} 子图{name}：对象 {len(sg['objects'])} · 关系 {len(sg['links'])}{detail}")

    # 关系端点自洽：每条关系的 from/to 类型都已声明（否则 OQL/Search Around 走不通）
    dangling = [(n, lt.from_type, lt.to_type) for (ns, n), lt in r.links.items() if ns == NS
                and ((NS, lt.from_type) not in r.objects or (NS, lt.to_type) not in r.objects)]
    if dangling:
        fails += 1
        print(f"  ✗ 悬空关系端点：{dangling}")
    else:
        print(f"  ✓ 所有关系端点自洽（{len(links)} 条关系的 from/to 均已声明）")

    if fails:
        print(f"\n✗ 子图贯通自检失败（{fails}）")
        return 1
    print("\n✓ 6 子图 schema 层全部贯通：对象/关系齐备、端点自洽、可 OQL/Search Around 导航")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
