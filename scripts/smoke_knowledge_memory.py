"""附着知识喂进 Memory 供 LLM 推理 smoke —— 知识→BACKGROUND→按相关性注入装配上下文。全离线。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.knowledge import load_into_memory
from clife_onto_engine.memory import MemoryStore, assemble
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401


def main() -> int:
    fails = 0
    mem = MemoryStore()
    n = load_into_memory(spi.registry, mem, "grass", "s1")
    print(f"== 装载知识入记忆：{n} 条 ==")
    ok0 = n >= 4
    fails += not ok0

    # 相关关键词（退化/盐碱化）→ 装配含诊断/处置手册知识
    ctx = assemble(mem, "grass", "s1", {"退化", "盐碱化", "修复"})
    hit = "盐碱化" in ctx.text or "处置手册" in ctx.text or "退化分级" in ctx.text
    print(f"== 相关 utterance→装配含知识（喂给 LLM）：{'✓' if hit else '✗'} ==")
    print("   装配片段：", ctx.text[:80].replace("\n", " "), "…")
    fails += not hit

    # 完全无关关键词 → 相关性低（BACKGROUND 预算内择优，退化知识不该占位）
    ctx2 = assemble(mem, "grass", "s1", {"xyz无关词"})
    # 无关时相关性 0，装配可能仍带（预算够）——重点验证相关性排序：相关词的命中数更高
    from clife_onto_engine.memory.retrieval import relevance
    deg = next(it for it in mem.by_layer.__self__._items.values() if "盐碱化" in it.content)
    r_rel = relevance(deg, {"退化", "盐碱化"})
    r_irr = relevance(deg, {"xyz无关词"})
    ok2 = r_rel > r_irr
    print(f"== 相关性排序（相关>无关）：{'✓' if ok2 else '✗'} · rel={r_rel} irr={r_irr} ==")
    fails += not ok2

    if fails:
        print(f"\n✗ 知识入记忆 smoke 失败（{fails}）"); return 1
    print("\n✓ 附着知识→Memory smoke 全通过：知识入 BACKGROUND · 相关性注入 · 供 LLM 推理")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
