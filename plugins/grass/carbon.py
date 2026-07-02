"""草碳·碳汇核算 —— 第三条 Action 闭环（子图5 碳汇-生态价值落地）。

`CarbonParcel →sequesters→ Methodology`：校验方法学年限/权属后按公式核算年固碳总量、出报告 +
碳汇数据凭证。与草修/草易同构，证明同一套内核零改动承载第三条业务闭环。
仍只 import clife_onto_engine.sdk，内核对碳汇一无所知。
"""
from __future__ import annotations

from clife_onto_engine.sdk import (
    Backing,
    HilPolicy,
    LinkType,
    ObjectType,
    ParamSpec,
    PropertySpec,
    RuleResult,
    Severity,
    spi,
)

from . import ONTOLOGY

# ---- 槽位 1：碳汇对象层（对齐方案 §5.4 #16/#17、§5.5 #22）--------------------
spi.registry.add_object(ObjectType(
    name="CarbonParcel", namespace=ONTOLOGY, primary_key="cp_id",
    properties=(
        PropertySpec("area_mu", "number", unit="亩", required=True),
        PropertySpec("years", "number", unit="年"),                 # 地块年限（碳汇计入期）
        PropertySpec("tenure", "string"),                          # 权属：清晰 / 争议
        PropertySpec("annual_seq_per_mu", "number", unit="tCO2e/亩·年"),  # 亩均年固碳
    )))
spi.registry.add_object(ObjectType(
    name="Methodology", namespace=ONTOLOGY, primary_key="method_no",
    properties=(PropertySpec("name", "string"), PropertySpec("min_years", "number"))))
spi.registry.add_object(ObjectType(
    name="CarbonReport", namespace=ONTOLOGY, primary_key="report_id",
    properties=(PropertySpec("cp_id", "string"), PropertySpec("annual_total", "number"),
                PropertySpec("methodology", "string"))))
spi.registry.add_link(LinkType("sequesters", ONTOLOGY, "CarbonParcel", "Methodology"))


# ---- 槽位 3：派生量 Function（年固碳总量 = 亩均固碳 × 面积）------------------
@spi.function(ONTOLOGY, "年固碳量核算", reads=("CarbonParcel",))
def annual_sequestration(ctx) -> float:
    cp = ctx.get("CarbonParcel", ctx.params["cp_id"]) or {}
    return round((cp.get("annual_seq_per_mu") or 0) * (cp.get("area_mu") or 0), 3)


# ---- 槽位 3：guard（declarative，角色）-------------------------------------
@spi.rule(ONTOLOGY, "碳汇角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def carbon_role(ctx) -> RuleResult:
    if ctx.actor.role not in {"碳汇开发", "监管", "生态运营"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权出碳汇核算")
    return RuleResult.ok()


# ---- 槽位 3：function-backed Rule（写后，查图谱）-------------------------
@spi.rule(
    ONTOLOGY, "方法学年限合规", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="地块年限不足方法学最低要求，已拦截",
    source="CCER 草原碳汇 / GEP 方法学的计入期年限要求",
    citations=("CCER 草原碳汇方法学",),
)
def methodology_years_ok(ctx) -> RuleResult:
    cp = ctx.get("CarbonParcel", ctx.params["cp_id"]) or {}
    mth = ctx.get("Methodology", ctx.params["method_no"]) or {}
    years, min_years = cp.get("years"), mth.get("min_years")
    if years is not None and min_years is not None and years < min_years:
        return RuleResult.fail(f"地块年限 {years} < 方法学最低 {min_years} 年",
                               suggestion=f"需满足计入期 ≥{min_years} 年或改用适配方法学")
    return RuleResult.ok()


@spi.rule(
    ONTOLOGY, "权属清晰", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="地块权属不清，不得开发碳汇",
    source="碳汇开发的权属清晰要求", citations=("CCER 草原碳汇方法学",),
)
def tenure_clear(ctx) -> RuleResult:
    cp = ctx.get("CarbonParcel", ctx.params["cp_id"]) or {}
    if cp.get("tenure") not in (None, "清晰"):
        return RuleResult.fail(f"权属为「{cp.get('tenure')}」，需清晰", suggestion="先完成确权再开发")
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "出碳汇核算报告",
    description="对碳汇地块按方法学核算年固碳总量并出报告（校验年限/权属）",
    params=(
        ParamSpec("cp_id", "ref(CarbonParcel)", required=True, description="碳汇地块 ID"),
        ParamSpec("method_no", "ref(Methodology)", required=True, description="采用的方法学编号"),
    ),
    guards=("碳汇角色权限",),
    post_rules=("方法学年限合规", "权属清晰"),
    writes=("CarbonReport",),
    validate_supported=True,
    hil=HilPolicy(reviewer_role="碳汇核证员",
                  predicate=lambda confidence, touched_hard: confidence < 0.75),
)
def emit_carbon_report(ctx) -> None:
    cp_id, method_no = ctx.params["cp_id"], ctx.params["method_no"]
    total = ctx.call_function("年固碳量核算")
    ctx.stage_write("CarbonReport", f"cr_{cp_id}", {
        "report_id": f"cr_{cp_id}", "cp_id": cp_id, "annual_total": total, "methodology": method_no})
    # 依方法学核算的固碳关系（CarbonParcel→sequesters→Methodology），供读层/多跳追溯
    ctx.stage_link("sequesters", "CarbonParcel", cp_id, "Methodology", method_no, 年固碳量=total)
    ctx.emit_effect("credential", on="committed", template="碳汇数据凭证", cp_id=cp_id)
    ctx.set_confidence(ctx.params.get("_confidence", 0.85))
    ctx.add_evidence(methodology=method_no)
    ctx.add_evidence(source="CCER 草原碳汇方法学")
