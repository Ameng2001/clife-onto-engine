"""辣椒分级 —— 辣椒插件的第二个 Action 闭环（对标 grass 的快检评级）。

同一套内核：派生量 Function（等级计算）+ 阈值拦截 Rule（残次拦截）+ 产出溯源码。
"""
from __future__ import annotations

from clife_onto_engine.sdk import Backing, HilPolicy, ParamSpec, RuleResult, Severity, spi

from . import ONTOLOGY

DEFECT_LIMIT = 0.15
REQUIRED = {"length", "SHU", "defect_rate"}


@spi.function(ONTOLOGY, "等级计算", reads=("GradeSample",))
def compute_grade(ctx) -> str:
    s = ctx.get("GradeSample", ctx.params["batch_id"]) or {}
    dr = s.get("defect_rate", 1.0)
    length = s.get("length", 0)
    if dr <= 0.02 and length >= 12:
        return "特级"
    if dr <= 0.05:
        return "一级"
    if dr <= 0.10:
        return "二级"
    return "等外"


@spi.rule(ONTOLOGY, "检测项完整", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def measurements_complete(ctx) -> RuleResult:
    missing = REQUIRED - set(ctx.params.get("measurements", {}))
    if missing:
        return RuleResult.fail(f"缺检测项：{sorted(missing)}", suggestion="补齐 length/SHU/defect_rate")
    return RuleResult.ok()


@spi.rule(ONTOLOGY, "分级角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def grading_role(ctx) -> RuleResult:
    if ctx.actor.role not in {"种植户", "合作社", "农技员", "收购商"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权分级")
    return RuleResult.ok()


@spi.rule(ONTOLOGY, "残次拦截", backing=Backing.FUNCTION, severity=Severity.HARD,
          message_template="残次率超标，禁止分级定价")
def defect_block(ctx) -> RuleResult:
    s = ctx.get("GradeSample", ctx.params["batch_id"]) or {}
    dr = s.get("defect_rate", 0)
    if dr > DEFECT_LIMIT:
        return RuleResult.fail(f"残次率 {dr} > {DEFECT_LIMIT}",
                               suggestion="该批次判为不合格，转人工复检")
    return RuleResult.ok()


@spi.action(
    ONTOLOGY, "辣椒分级",
    description="对一批辣椒按长度/辣度/残次率分级并出溯源码",
    params=(
        ParamSpec("batch_id", "string", required=True, description="采收批次号"),
        ParamSpec("measurements", "object", required=True, description="检测值 length/SHU/defect_rate 等"),
    ),
    guards=("检测项完整", "分级角色权限"),
    post_rules=("残次拦截",),
    writes=("GradeSample",),
    validate_supported=True,
    hil=HilPolicy(reviewer_role="分级定价员",
                  predicate=lambda confidence, touched_hard: confidence < 0.70),
)
def grade_chili(ctx) -> None:
    batch = ctx.params["batch_id"]
    m = ctx.params["measurements"]
    ctx.stage_write("GradeSample", batch, {**m, "batch_id": batch})
    grade = ctx.call_function("等级计算")
    ctx.stage_write("GradeSample", batch, {**m, "batch_id": batch, "grade": grade, "trace_code": f"CH-{batch}"})
    ctx.emit_effect("credential", on="committed", template="辣椒溯源凭证", batch_id=batch)
    ctx.set_confidence(m.get("_confidence", 0.9))
    ctx.add_evidence(standard="GB/T 辣椒分级标准")
