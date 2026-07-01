"""知识影响力对比 harness —— 同一句口语，load_knowledge 关/开各跑一次，看 LLM 变没变。

证明的不是"知识进了上下文"（那已验过），而是"知识**改变了 LLM 的选择**"——知识层押注的核心价值。

做法：两个 Session（知识 off / on）跑同一批**知识敏感**口语；用 SpyCompiler 录下每次
编译时喂给 LLM 的 memory_text，并排打印"喂了什么知识 + LLM 编成什么 + 回了什么"。
  · CI/桩：SpyCompiler 断言"知识确实到了 LLM 手上"（管道通）；桩不读 memory_text 故行为不变（诚实）。
  · 真 Qwen：并排看两次的**行为差异**（人判：有知识那次是否更贴处置手册/更对）。

用法：
  python scripts/e2e_knowledge_influence.py            # 有 llm.local.json 走真 Qwen，否则走桩
  python scripts/e2e_knowledge_influence.py --stub     # 强制桩（只验管道）
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

from scripts.e2e_harness import ScriptedCompiler, make_compiler, seed  # 复用数据+编译器选择

import plugins.grass  # noqa: F401


class SpyCompiler:
    """录下每次编译时喂给 LLM 的 memory_text，再委托内层编译器。"""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.calls: list[dict] = []

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        self.calls.append({"utterance": utterance, "memory_text": memory_text})
        return self.inner.compile(ontology_id, utterance,
                                  memory_text=memory_text, actor_role=actor_role)


# 知识敏感口语：判断/处置类，正确答案落在 Degradation 的诊断/处置手册知识里
UTTERANCES = [
    "parcel_001 是重度盐碱地，接下来该先做什么？",
    "这块地退化挺严重的，直接喷播碱茅行不行？",
]


def _reply_brief(r) -> str:
    if r.kind == "query":
        return f"[查询] {len(r.rows or [])} 行"
    if r.kind == "committed":
        return f"[已执行] {list(r.written)}"
    if r.kind == "rejected":
        return f"[拒绝] {[v.rule for v in r.violations]}"
    if r.kind == "advise":
        return f"[建议] {r.answer}"
    if r.kind == "clarify":
        return f"[澄清] {r.question}"
    return f"[错误] {r.error}"


def _session(store, compiler, load_knowledge, sid):
    return Session(ontology_id="grass", registry=spi.registry, store=store,
                   compiler=compiler, actor=Actor("u1", "施工方"),
                   session_id=sid, schema_version="grass@0.1.0",
                   load_knowledge=load_knowledge)


def main() -> int:
    force_stub = "--stub" in sys.argv
    base = make_compiler(force_stub)          # 真 Qwen 或桩
    spy_off = SpyCompiler(base)
    spy_on = SpyCompiler(base)

    s_off = _session(seed(), spy_off, False, "kn_off")
    s_on = _session(seed(), spy_on, True, "kn_on")

    for u in UTTERANCES:
        r_off = s_off.ask(u)
        r_on = s_on.ask(u)
        km_off = spy_off.calls[-1]["memory_text"]
        km_on = spy_on.calls[-1]["memory_text"]
        kn_in_off = any(w in km_off for w in ("处置手册", "改良", "盐碱化多因"))
        kn_in_on = any(w in km_on for w in ("处置手册", "改良", "盐碱化多因"))
        print(f"\n口语：{u}")
        print(f"  [无知识] 喂 LLM 含知识={kn_in_off} → {_reply_brief(r_off)}")
        print(f"  [有知识] 喂 LLM 含知识={kn_in_on} → {_reply_brief(r_on)}")
        differ = (r_off.kind, getattr(r_off, 'action', None), r_off.question, r_off.answer) != \
                 (r_on.kind, getattr(r_on, 'action', None), r_on.question, r_on.answer)
        print(f"  行为差异：{'有（知识改变了 LLM）' if differ else '无（桩下正常；真 Qwen 下若也无，说明该场景知识没起作用）'}")

    # CI/桩可断言的：知识确实到了「有知识」那次的 LLM 手上，「无知识」那次没有（管道通）
    on_has = any(any(w in c["memory_text"] for w in ("处置手册", "改良", "盐碱化多因")) for c in spy_on.calls)
    off_has = any(any(w in c["memory_text"] for w in ("处置手册", "改良", "盐碱化多因")) for c in spy_off.calls)
    ok = on_has and not off_has
    print(f"\n== 管道：知识到达 LLM（有知识那次 memory_text 含知识、无知识那次不含）：{'✓' if ok else '✗'} ==")
    if force_stub or isinstance(base, ScriptedCompiler):
        print("   （当前是桩：只验管道通；行为差异需真 Qwen 才见——去掉 --stub 并配好 llm.local.json）")
    else:
        print("   （真 Qwen：请人判上面每句『有知识 vs 无知识』的行为差异是否更贴处置手册/更对）")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
