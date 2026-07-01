"""端到端验证 harness —— 把整栈在真实感数据上压一遍，一键切桩/真 Qwen。

跑的是完整产品回路（口语 → 记忆接地 + 知识注入 → 意图编译 → 查 OQL / 做 Action（guard→
写后规则→确定性回滚→审计）→ 回写记忆），一个脚本端到端压 Session。

模式：
  · 默认离线：无 llm.local.json / 无 LLM env 时用**脚本编译器**（确定性，作参照行为）。
  · 真 Qwen：放好 llm.local.json（或设 DASHSCOPE_*）即自动切**真 IntentCompiler**——
    这时看真 LLM 到底选没选对动作、记忆/知识有没有帮上、治理有没有兜住。

用法：
  python scripts/e2e_harness.py            # 自动：有 LLM 配置走真、否则走桩
  python scripts/e2e_harness.py --stub     # 强制桩
  python scripts/e2e_harness.py --explorer # 跑完导出对象图 Explorer 到 build/explorer/e2e.html
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore, StagedLink
from clife_onto_engine.query.oql import Cond, OQLQuery
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

import plugins.grass  # noqa: F401


# ---- 真实感数据（两个盟市、不同乡土名录，让治理有意义）----
def seed() -> InMemoryStore:
    s = InMemoryStore()
    # 巴彦淖尔·盐碱
    s.put_object("Site", "parcel_001", {"parcel_id": "parcel_001", "area_mu": 500,
                                        "region": "巴彦淖尔", "site_type": "盐碱"})
    for sp in ("碱茅", "星星草", "披碱草"):
        s.put_object("NativeListing", f"巴彦淖尔::{sp}", {"region": "巴彦淖尔", "species": sp})
    # 锡林郭勒·草原（乡土名录不同：碱茅在这里不算乡土）
    s.put_object("Site", "parcel_002", {"parcel_id": "parcel_002", "area_mu": 800,
                                        "region": "锡林郭勒", "site_type": "草原"})
    for sp in ("冰草", "羊草"):
        s.put_object("NativeListing", f"锡林郭勒::{sp}", {"region": "锡林郭勒", "species": sp})
    # 修复推理主干（供多跳查询）
    s.put_object("Degradation", "deg_001", {"deg_id": "deg_001", "level": "重度", "type": "盐碱化"})
    for m, n in (("m_pen", "喷播"), ("m_sup", "补播")):
        s.put_object("RestorationMethod", m, {"method_id": m, "name": n})
    s.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg_001"))
    s.put_link(StagedLink("treated_by", "Degradation", "deg_001", "RestorationMethod", "m_pen"))
    return s


# ---- 脚本编译器（离线参照行为；真 Qwen 时不用它）----
class ScriptedCompiler:
    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        u = utterance
        if "哪些地块" in u:
            region = "巴彦淖尔" if "巴彦淖尔" in u else "锡林郭勒"
            return CompiledIntent("query", confidence=0.9,
                oql=OQLQuery(namespace=ontology_id, start="Site",
                             where=(Cond("region", "eq", region),)))
        if "修复方法" in u or "怎么治" in u:
            return CompiledIntent("query", confidence=0.85,
                oql=OQLQuery(namespace=ontology_id, start="Site",
                             where=(Cond("parcel_id", "eq", "parcel_001"),),
                             steps=(__import__("clife_onto_engine.query.oql", fromlist=["Step"]).Step("suffers"),)))
        if u.startswith("给 parcel_") and "出" in u:
            site = "parcel_002" if "parcel_002" in u else "parcel_001"
            species = ["紫花苜蓿"] if "紫花苜蓿" in u else (["碱茅"] if "碱茅" in u else ["冰草"])
            return CompiledIntent("action", action="出一地一方", confidence=0.82,
                params={"site_id": site, "species": species, "budget": 300})
        if "帮我出" in u or "出个方案" in u:
            return CompiledIntent("clarify", confidence=0.4, question="请补充：地块 ID、拟用草种、预算？")
        return CompiledIntent("clarify", confidence=0.3, question="没听懂，请换个说法")


def make_compiler(force_stub: bool):
    if not force_stub:
        try:
            from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
            client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
            print(f"== 模式：真 Qwen · model={client.model} ==\n")
            return IntentCompiler(client, spi.registry)
        except Exception as e:  # 无配置/无 openai 包 → 回落桩
            print(f"== 模式：脚本编译器（离线参照）· 无 LLM 配置（{type(e).__name__}）==\n")
    else:
        print("== 模式：脚本编译器（--stub 强制）==\n")
    return ScriptedCompiler()


# ---- 端到端剧本（一段 施工方 会话，含治理兜底 money-shot）----
STEPS = [
    "巴彦淖尔有哪些地块？",
    "parcel_001 能用哪些修复方法？",
    "给 parcel_001 出一地一方，用碱茅，预算300",          # 合规（碱茅是巴彦淖尔乡土）→ 应 committed
    "给 parcel_001 出方案，用紫花苜蓿，预算300",           # 违规（非乡土）→ 应被乡土合规兜住
    "给 parcel_002 出方案，用碱茅，预算300",               # 跨区域用错草种（碱茅非锡林郭勒乡土）→ 应被兜住
    "帮我出个方案",                                         # 缺参 → 应澄清
]


def main() -> int:
    force_stub = "--stub" in sys.argv
    compiler = make_compiler(force_stub)
    store = seed()
    session = Session(ontology_id="grass", registry=spi.registry, store=store,
                      compiler=compiler, actor=Actor("u1", "施工方"),
                      session_id="e2e", schema_version="grass@0.1.0", load_knowledge=True)

    stats = {"query": 0, "committed": 0, "rejected": 0, "clarify": 0, "error": 0}
    for i, utt in enumerate(STEPS, 1):
        print(f"[{i}] 施工方：{utt}")
        r = session.ask(utt)
        stats[r.kind if r.kind in stats else "error"] = stats.get(r.kind, 0) + 1
        if r.kind == "query":
            print(f"    → [查询] {len(r.rows or [])} 行 · {(r.rows or [])[:3]}")
        elif r.kind == "committed":
            print(f"    → [已执行] 写入 {list(r.written)} · 置信 {r.confidence}")
        elif r.kind == "rejected":
            for v in r.violations:
                print(f"    → [本体兜底·拒绝] 违反「{v.rule}」：{v.message} · 建议：{v.suggestion}")
        elif r.kind == "clarify":
            print(f"    → [澄清] {r.question}")
        else:
            print(f"    → [错误] {r.error}")
        print()

    print("== 端到端汇总 ==")
    print(f"   查询 {stats['query']} · 提交 {stats['committed']} · 治理拒绝 {stats['rejected']} · "
          f"澄清 {stats['clarify']} · 错误 {stats['error']}")
    audits = session.engine.audit.query("grass")
    print(f"   审计留痕 {len(audits)} 条 · 决策分布：",
          {d: sum(1 for a in audits if a.decision == d) for d in {a.decision for a in audits}})

    # 关键断言（桩模式下应恒成立；真 Qwen 下若不成立就是暴露了真问题）
    ok = stats["committed"] >= 1 and stats["rejected"] >= 1
    print(f"\n   OAG 回路核心（既有合规提交、又有本体兜底拒绝）：{'✓ 成立' if ok else '✗ 未成立（真 LLM 下值得深挖）'}")

    if "--explorer" in sys.argv:
        from clife_onto_engine.explorer import render
        cyto = (ROOT / "third-party" / "okf-visualizer" / "reference_agent" / "viewer"
                / "static" / "vendor" / "cytoscape.min.js").read_text(encoding="utf-8")
        out = ROOT / "build" / "explorer" / "e2e.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(spi.registry, store, "grass", cytoscape_js=cyto), encoding="utf-8")
        print(f"\n   对象图 Explorer → {out.relative_to(ROOT)}")

    return 0 if ok or not force_stub else 1


if __name__ == "__main__":
    raise SystemExit(main())
