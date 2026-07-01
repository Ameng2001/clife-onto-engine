"""CQ 验收回路（C3）—— 声明式 competency question 套件，对某本体版本跑 pass/fail。

闭合建模→运行时环：建模端改本体产出新版本 → 对新版本跑 CQ 套件 → pass/fail 回喂建模端。
CQ 也是版本演进的**能力回归门**——同一套 CQ 对不同版本跑，某版本削弱了某规则即被抓。

两类 CQ：
  · ActionCQ：动作的期望裁决（该 commit / 该被某规则拦）——走 `validate`（无副作用）。
  · QueryCQ：查询的期望结果（至少 N 行）——走 `oql.execute`。

内核只提供 `run_cq_suite`，**不含任何具体 CQ**（套件由插件/建模端提供）。与行业无关（CI 强制）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .kernel import ActionEngine
from .query import InMemoryStore, QueryView
from .query.oql import execute as oql_execute
from .sdk.context import Actor


@dataclass(frozen=True)
class ActionCQ:
    name: str
    ontology: str
    action: str
    params: dict
    actor_role: str
    expect: str                       # commit | reject
    expect_rule: Optional[str] = None  # 期望被哪条规则拦（expect=reject 时可选）
    kind: str = "action"


@dataclass(frozen=True)
class QueryCQ:
    name: str
    ontology: str
    oql: object                       # OQLQuery
    min_rows: int = 1
    kind: str = "query"


@dataclass(frozen=True)
class CQResult:
    name: str
    kind: str
    passed: bool
    expected: str
    actual: str
    detail: str = ""


@dataclass(frozen=True)
class CQReport:
    total: int
    passed: int
    failed: int
    results: tuple[CQResult, ...] = ()

    @property
    def ok(self) -> bool:
        return self.failed == 0

    @property
    def summary(self) -> str:
        return f"CQ 验收：{self.passed}/{self.total} 通过 · 失败 {self.failed}"


def _run_action_cq(cq: ActionCQ, registry, store) -> CQResult:
    engine = ActionEngine(registry, store=store if store is not None else InMemoryStore())
    actor = Actor("cq", cq.actor_role)
    exp = f"{cq.expect}" + (f"·{cq.expect_rule}" if cq.expect_rule else "")
    try:
        prev = engine.validate(cq.ontology, cq.action, dict(cq.params), actor)
    except Exception as e:  # validate_supported=False / 未注册
        return CQResult(cq.name, "action", False, exp, "error", f"{type(e).__name__}: {e}")
    rules = [v.rule for v in prev.violations]
    if cq.expect == "commit":
        passed = prev.would_commit
        actual = "commit" if prev.would_commit else f"reject·{rules}"
    else:  # reject
        passed = (not prev.would_commit) and (cq.expect_rule is None or cq.expect_rule in rules)
        actual = f"reject·{rules}" if not prev.would_commit else "commit"
    detail = "" if passed else f"期望 {exp}，实际 {actual}"
    return CQResult(cq.name, "action", passed, exp, actual, detail)


def _run_query_cq(cq: QueryCQ, registry, store) -> CQResult:
    exp = f"≥{cq.min_rows} 行"
    try:
        res = oql_execute(cq.oql, QueryView(store if store is not None else InMemoryStore(), []), registry)
    except Exception as e:
        return CQResult(cq.name, "query", False, exp, "error", f"{type(e).__name__}: {e}")
    n = len(res.rows)
    passed = n >= cq.min_rows
    return CQResult(cq.name, "query", passed, exp, f"{n} 行",
                    "" if passed else f"期望 {exp}，实际 {n} 行")


def run_cq_suite(cqs, registry, *, store=None) -> CQReport:
    """对给定 registry（活的或某本体版本）逐条跑 CQ，产出 pass/fail 报告。只读。"""
    results = []
    for cq in cqs:
        if getattr(cq, "kind", "") == "query":
            results.append(_run_query_cq(cq, registry, store))
        else:
            results.append(_run_action_cq(cq, registry, store))
    passed = sum(1 for r in results if r.passed)
    return CQReport(total=len(results), passed=passed, failed=len(results) - passed,
                    results=tuple(results))
