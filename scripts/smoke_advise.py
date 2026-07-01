"""咨询路径 advise smoke —— 知识接地的只读建议：不进引擎、不写库、进记忆。全离线。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.memory import Layer
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

import plugins.grass  # noqa: F401


class _AdviseCompiler:
    """桩：判断类→advise(基于处置手册)；否则澄清。"""
    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        if "先做什么" in utterance or "行不行" in utterance:
            return CompiledIntent("advise", confidence=0.8,
                answer="重度盐碱地需先进行工程或化学改良，再喷播乡土草种、后期封育；直接喷播可能无法成活。")
        return CompiledIntent("clarify", confidence=0.4, question="请补充信息")


def main() -> int:
    fails = 0
    store = InMemoryStore(); plugins.grass.seed_reference_data(store)
    s = Session(ontology_id="grass", registry=spi.registry, store=store,
                compiler=_AdviseCompiler(), actor=Actor("u1", "施工方"),
                session_id="adv", schema_version="grass@0.1.0", load_knowledge=True)

    before = {(t, k) for (t, k) in [] }  # 占位
    r = s.ask("parcel_001 重度盐碱地，接下来先做什么？")
    ok = r.kind == "advise" and "改良" in r.answer
    print(f"== 判断类→只读建议：{'✓' if ok else '✗'} · {r.summary()} ==")
    fails += not ok

    # 只读：无任何写、审计无新增（advise 不进 Action 引擎）
    no_write = store.get_object("Project", "proj_parcel_001") is None
    no_audit = len(s.engine.audit.query("grass")) == 0
    print(f"== 只读（不写库、审计无写）：{'✓' if no_write and no_audit else '✗'} ==")
    fails += not (no_write and no_audit)

    # 建议进 CONTEXT 记忆
    ctx = [it for it in s.memory.by_layer(Layer.CONTEXT, "grass", "adv") if it.source == "advise"]
    print(f"== 建议进记忆：{'✓' if ctx else '✗'} ==")
    fails += not ctx

    # 做/查不受影响：查询照常
    r2 = s.ask("随便说")  # → clarify
    print(f"== 澄清路径不受影响：{'✓' if r2.kind == 'clarify' else '✗'} ==")
    fails += not (r2.kind == "clarify")

    if fails:
        print(f"\n✗ advise smoke 失败（{fails}）"); return 1
    print("\n✓ 咨询路径 advise smoke 全通过：知识接地只读建议 · 不写库 · 进记忆 · 不改既有路径")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
