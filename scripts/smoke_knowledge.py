"""附着知识 smoke（多场景知识：吸收 Palantir 统一图 + UModel 模板化）。全离线。

一次取"对象 + 它的知识"（Palantir 式）；知识按标准 kind 声明（UModel 式）；
与强制 Rule / 派生 Function 并存。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.knowledge import knowledge_for, knowledge_of_kind
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401


def main() -> int:
    fails = 0
    # 1) 对象 + 知识一次取到（Palantir 式统一）
    deg = knowledge_for(spi.registry, "grass", "Degradation")
    ok = len(deg) == 2 and {k.kind for k in deg} == {"diagnostic", "playbook"}
    print(f"== Degradation 附着知识（诊断+处置手册）：{'✓' if ok else '✗'} · {[(k.kind,k.name) for k in deg]} ==")
    fails += not ok

    # 2) 标准 kind 覆盖（UModel 式模板化）：template/diagnostic/playbook/reference
    kinds = set()
    for ot in ("Site", "Degradation", "RestorationMethod"):
        for k in knowledge_for(spi.registry, "grass", ot):
            kinds.add(k.kind)
    ok2 = {"template", "diagnostic", "playbook", "reference"} <= kinds
    print(f"== 四类知识全覆盖：{'✓' if ok2 else '✗'} · {sorted(kinds)} ==")
    fails += not ok2

    # 3) 按 kind 过滤
    tpl = knowledge_of_kind(spi.registry, "grass", "Site", "template")
    ok3 = len(tpl) == 1 and tpl[0].kind == "template"
    print(f"== 按 kind 过滤（Site 的 template）：{'✓' if ok3 else '✗'} ==")
    fails += not ok3

    # 4) 无绑定对象为空 + 与强制知识并存（乡土合规仍是 Rule）
    ok4 = knowledge_for(spi.registry, "grass", "NativeListing") == () \
        and ("grass", "乡土合规") in spi.registry.rules
    print(f"== 无绑定为空 + 强制知识(Rule)并存：{'✓' if ok4 else '✗'} ==")
    fails += not ok4

    if fails:
        print(f"\n✗ 附着知识 smoke 失败（{fails}）"); return 1
    print("\n✓ 附着知识 smoke 全通过：对象+知识一次取 · 四类标准化 · 与 Rule/Function 并存")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
