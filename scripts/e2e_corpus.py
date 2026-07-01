"""端到端场景语料 —— 把读/写全面覆盖成一张矩阵，桩进 CI、真 Qwen 可抽检。

每个场景自带：口语（送真 Qwen）+ 确定性参照意图 stub_intent（桩用）+ 期望 kind + 结果断言。
  · 桩模式（默认无 LLM / --stub）：ScriptedCompiler 返回 stub_intent → 断言每条 kind+结果（进 CI）。
  · 真 Qwen（有 llm.local.json）：口语过真 LLM，逐条报「LLM 编对没、结果对不对」→ 意图编译跨面准确率。

覆盖：grass + chili 两插件的 4 个动作各（提交+拒绝）、多种读（简单/多跳/聚合）、advise、clarify。
（说明：遥测 plan / Explorer 是独立端点，由各自测试覆盖，不在口语回路语料内；HIL 待审已在
ask 回路 surface 为 pending_hil（见 tests/test_hil_surface.py）——本语料聚焦意图→执行的读写面。）
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass
from typing import Callable, Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.oql import Aggregate, Cond, OQLQuery, Step
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401


def _q(ns, start, where=(), steps=(), aggregate=None):
    return CompiledIntent("query", confidence=0.9,
        oql=OQLQuery(namespace=ns, start=start, where=where, steps=steps, aggregate=aggregate))


def _a(action, **params):
    return CompiledIntent("action", action=action, params=params, confidence=0.85)


@dataclass
class Scenario:
    name: str
    ontology: str
    actor_role: str
    utterance: str
    stub_intent: CompiledIntent
    expect_kind: str
    check: Callable          # (reply) -> bool
    face: str                # 读 | 写 | 咨询 | 澄清


CP_OK = {"CP": 18, "NDF": 40, "ADF": 30, "RFV": 150, "霉菌毒素": 0.01}
CP_MOLD = {"CP": 18, "NDF": 40, "ADF": 30, "RFV": 150, "霉菌毒素": 0.2}
CH_OK = {"length": 14, "SHU": 5000, "defect_rate": 0.03}
CH_BAD = {"length": 10, "SHU": 5000, "defect_rate": 0.5}


def _has_rule(rule):
    return lambda r: any(v.rule == rule for v in r.violations)


SCENARIOS = [
    # ---- grass 读 ----
    Scenario("查地块·简单", "grass", "施工方", "巴彦淖尔有哪些地块？",
             _q("grass", "Site", (Cond("region", "eq", "巴彦淖尔"),)),
             "query", lambda r: len(r.rows or []) >= 1, "读"),
    Scenario("查修复方法·多跳", "grass", "施工方", "parcel_001 能用哪些修复方法？",
             _q("grass", "Site", (Cond("parcel_id", "eq", "parcel_001"),), (Step("suffers"),)),
             "query", lambda r: r.rows is not None, "读"),
    Scenario("统计地块·聚合", "grass", "施工方", "巴彦淖尔有多少个地块？",
             _q("grass", "Site", (Cond("region", "eq", "巴彦淖尔"),), aggregate=Aggregate("count")),
             "query", lambda r: bool(r.rows), "读"),
    # ---- grass 写：出一地一方 ----
    Scenario("出一地一方·提交", "grass", "施工方", "给 parcel_001 出一地一方，用碱茅，预算300",
             _a("出一地一方", site_id="parcel_001", species=["碱茅"], budget=300),
             "committed", lambda r: bool(r.written), "写"),
    Scenario("出一地一方·非乡土拒绝", "grass", "施工方", "给 parcel_001 出方案，用紫花苜蓿，预算300",
             _a("出一地一方", site_id="parcel_001", species=["紫花苜蓿"], budget=300),
             "rejected", _has_rule("乡土合规"), "写"),
    # ---- grass 写：快检评级 ----
    Scenario("快检评级·提交", "grass", "施工方", "给草样 batch_A 快检评级，CP18 NDF40 ADF30 RFV150 霉菌毒素0.01",
             _a("快检评级", batch_id="batch_A", measurements=CP_OK),
             "committed", lambda r: bool(r.written), "写"),
    Scenario("快检评级·霉变拦截", "grass", "施工方", "给草样 batch_B 快检评级，CP18 NDF40 ADF30 RFV150 霉菌毒素0.2",
             _a("快检评级", batch_id="batch_B", measurements=CP_MOLD),
             "rejected", _has_rule("霉变拦截"), "写"),
    # ---- grass 咨询 / 澄清 ----
    Scenario("咨询·处置建议", "grass", "施工方", "parcel_001 重度盐碱地接下来先做什么？",
             CompiledIntent("advise", confidence=0.8, answer="重度盐碱地需先工程/化学改良，再喷播乡土草种、后期封育。"),
             "advise", lambda r: bool(r.answer), "咨询"),
    Scenario("澄清·缺参", "grass", "施工方", "帮我出个方案",
             CompiledIntent("clarify", confidence=0.4, question="请补充 site_id/species/budget"),
             "clarify", lambda r: bool(r.question), "澄清"),
    # ---- chili 读 ----
    Scenario("查地块·chili", "chili", "种植户", "海南有哪些地块？",
             _q("chili", "Field", (Cond("region", "eq", "海南"),)),
             "query", lambda r: len(r.rows or []) >= 1, "读"),
    # ---- chili 写：制定种植方案 ----
    Scenario("制定种植方案·提交", "chili", "种植户", "给 field_001 制定种植方案，朝天椒，密度2200，预算500",
             _a("制定种植方案", field_id="field_001", variety="朝天椒", density=2200, budget=500),
             "committed", lambda r: bool(r.written), "写"),
    Scenario("制定种植方案·品种不适配拒绝", "chili", "种植户", "给 field_001 制定方案，用紫天椒，密度2200，预算500",
             _a("制定种植方案", field_id="field_001", variety="紫天椒", density=2200, budget=500),
             "rejected", _has_rule("品种适配"), "写"),
    # ---- chili 写：辣椒分级 ----
    Scenario("辣椒分级·提交", "chili", "种植户", "给批次 g_A 辣椒分级，length14 SHU5000 defect_rate0.03",
             _a("辣椒分级", batch_id="g_A", measurements=CH_OK),
             "committed", lambda r: bool(r.written), "写"),
    Scenario("辣椒分级·残次拦截", "chili", "种植户", "给批次 g_B 辣椒分级，length10 SHU5000 defect_rate0.5",
             _a("辣椒分级", batch_id="g_B", measurements=CH_BAD),
             "rejected", _has_rule("残次拦截"), "写"),
]


class ScriptedCompiler:
    """按口语返回该场景的确定性参照意图（桩/CI 用）。"""
    def __init__(self, scenarios):
        self._by_utt = {s.utterance: s.stub_intent for s in scenarios}

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        return self._by_utt.get(utterance,
                                CompiledIntent("clarify", confidence=0.3, question="未识别"))


class _SpyCompiler:
    """录下内层编译器对每句口语实际产出的 CompiledIntent（看真 LLM 抽了什么/编了什么）。"""
    def __init__(self, inner):
        self.inner = inner
        self.last: dict = {}

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        ci = self.inner.compile(ontology_id, utterance,
                                memory_text=memory_text, actor_role=actor_role)
        self.last[utterance] = ci
        return ci


def _intent_detail(ci) -> str:
    """把 LLM 编译结果打成一行可读（重点是它实际抽的参数/编的 OQL）。"""
    if ci is None:
        return "（未捕获）"
    if ci.kind == "action":
        return f"动作={ci.action} 参数={ci.params}"
    if ci.kind == "query" and ci.oql is not None:
        q = ci.oql
        where = [(c.field, c.op, c.value) for c in q.where]
        steps = [s.link_type for s in q.steps]
        agg = f"{q.aggregate.func}" if q.aggregate else None
        return f"OQL start={q.start} where={where} steps={steps} agg={agg}"
    if ci.kind == "advise":
        return f"建议={ci.answer}"
    if ci.kind == "clarify":
        return f"追问={ci.question}"
    return f"{ci.kind} {ci.error}"


def _seed(ontology):
    s = InMemoryStore()
    (plugins.grass if ontology == "grass" else plugins.chili).seed_reference_data(s)
    return s


def make_compiler(force_stub, scenarios):
    if not force_stub:
        try:
            from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
            client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
            print(f"== 模式：真 Qwen · model={client.model} ==")
            return IntentCompiler(client, spi.registry), True
        except Exception as e:
            print(f"== 模式：脚本编译器（离线参照）· 无 LLM（{type(e).__name__}）==")
    else:
        print("== 模式：脚本编译器（--stub）==")
    return ScriptedCompiler(scenarios), False


def run(scenarios, *, force_stub=False, verbose=False):
    compiler, live = make_compiler(force_stub, scenarios)
    spy = _SpyCompiler(compiler)
    # 每 (本体, 角色) 一个会话（角色权限不同）
    sessions: dict = {}
    passed = failed = 0
    by_face: dict = {}
    for sc in scenarios:
        key = (sc.ontology, sc.actor_role)
        if key not in sessions:
            sessions[key] = Session(ontology_id=sc.ontology, registry=spi.registry,
                                    store=_seed(sc.ontology), compiler=spy,
                                    actor=Actor("u", sc.actor_role), session_id=f"{key}",
                                    schema_version=f"{sc.ontology}@0.1.0", load_knowledge=True)
        r = sessions[key].ask(sc.utterance)
        ok = r.kind == sc.expect_kind and sc.check(r)
        passed += ok; failed += (not ok)
        by_face.setdefault(sc.face, [0, 0])
        by_face[sc.face][0] += ok; by_face[sc.face][1] += 1
        mark = "✓" if ok else "✗"
        detail = f"kind={r.kind}"
        if r.kind == "rejected":
            detail += f"·{[v.rule for v in r.violations]}"
        elif r.kind == "committed":
            detail += f"·{list(r.written)}"
        print(f"  {mark} [{sc.face}] {sc.name} · 期望 {sc.expect_kind} · 实得 {detail}")
        if verbose or live:  # 展示 LLM 实际编译内容（真 Qwen 下即真实回答）
            print(f"       口语「{sc.utterance}」")
            print(f"       LLM 编成：{_intent_detail(spy.last.get(sc.utterance))}")
    print(f"\n== 覆盖矩阵：{passed}/{passed+failed} 通过 · 按面 "
          + " · ".join(f"{f} {v[0]}/{v[1]}" for f, v in by_face.items()) + " ==")
    return passed, failed


def main() -> int:
    force_stub = "--stub" in sys.argv
    verbose = "--verbose" in sys.argv
    passed, failed = run(SCENARIOS, force_stub=force_stub, verbose=verbose)
    if failed and (force_stub or isinstance(make_compiler(True, SCENARIOS)[0], ScriptedCompiler)):
        return 1  # 桩下必须全过
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
