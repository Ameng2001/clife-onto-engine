"""草育·杂交组合推荐 —— 第四条 Action 闭环（子图4 育种落地）。

育种员提一对亲本 + 目标性状，引擎校验亲本合规 + 目标性状有标记基础，按标记效应预测杂交增益、
出杂交组合方案 + `crossed_to` 关系。与草修/草易/草碳同构。

设计取舍（同 adapts_to 先例）：标记-性状关系用 Germplasm 的 `trait_markers` **属性**（{性状: 效应}）
承载而非边——因 tenant ingest 不支持边加载，属性可经 JSONL ingest、seed 与 tenant 两路一致。
GeneMarker/marks/carries_marker 边留 subgraphs 作导航/未来（tenant 支持关系源后可切边形态）。
仍只 import clife_onto_engine.sdk。
"""
from __future__ import annotations

from clife_onto_engine.sdk import (
    Backing,
    EdgeSemantics,
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

# ---- 槽位 1：育种对象层（对齐方案 §5.4 #3、§5.5 #5）------------------------
spi.registry.add_object(ObjectType(
    name="Germplasm", namespace=ONTOLOGY, primary_key="germplasm_id",
    properties=(
        PropertySpec("species", "string"),
        PropertySpec("germination", "number", unit="%"),
        PropertySpec("trait_markers", "object"),   # {性状: 聚合标记效应}，驱动预测增益（属性形态）
    )))
spi.registry.add_object(ObjectType(
    name="CrossPlan", namespace=ONTOLOGY, primary_key="plan_id",
    properties=(PropertySpec("base", "string"), PropertySpec("candidate", "string"),
                PropertySpec("target_trait", "string"), PropertySpec("predicted_gain", "number"))))
spi.registry.add_link(LinkType("crossed_to", ONTOLOGY, "Germplasm", "Germplasm",
                               edge_semantics=EdgeSemantics.HYPOTHESIS))


# ---- 槽位 3：派生量 Function（预测增益 = 候选亲本对目标性状的聚合标记效应）----
@spi.function(ONTOLOGY, "杂交预测增益", reads=("Germplasm",))
def cross_gain(ctx) -> float:
    cand = ctx.get("Germplasm", ctx.params["candidate_id"]) or {}
    tm = cand.get("trait_markers") or {}
    return round(float(tm.get(ctx.params["target_trait"], 0) or 0), 3)


# ---- 槽位 3：guard（declarative，角色）-------------------------------------
@spi.rule(ONTOLOGY, "育种角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def breeding_role(ctx) -> RuleResult:
    if ctx.actor.role not in {"育种", "科研", "种业科研"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权做杂交推荐")
    return RuleResult.ok()


# ---- 槽位 3：function-backed Rule（写后，查图谱）-------------------------
@spi.rule(ONTOLOGY, "亲本合规", backing=Backing.FUNCTION, severity=Severity.HARD,
          message_template="亲本不合规，已拦截", source="杂交亲本有效性要求")
def parents_valid(ctx) -> RuleResult:
    base, cand = ctx.params["base_id"], ctx.params["candidate_id"]
    if base == cand:
        return RuleResult.fail("亲本不能相同", suggestion="选两个不同种质")
    if ctx.get("Germplasm", base) is None:
        return RuleResult.fail(f"种质 {base} 不存在")
    if ctx.get("Germplasm", cand) is None:
        return RuleResult.fail(f"种质 {cand} 不存在")
    return RuleResult.ok()


@spi.rule(
    ONTOLOGY, "目标性状可预测", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="候选亲本无该目标性状的标记基础，已拦截",
    source="全基因组选择需目标性状有关联标记（marks）",
    citations=("60K 液相基因芯片 GWAS 标记-性状关联",),
)
def trait_predictable(ctx) -> RuleResult:
    if ctx.call_function("杂交预测增益") <= 0:
        return RuleResult.fail("候选亲本不携带 marks 目标性状的标记（预测增益=0）",
                               suggestion="换携带目标性状标记的候选亲本")
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "出杂交组合推荐",
    description="对一对亲本 + 目标性状，校验合规并按标记效应预测增益、出杂交组合方案",
    params=(
        ParamSpec("base_id", "ref(Germplasm)", required=True, description="基础亲本种质 ID"),
        ParamSpec("candidate_id", "ref(Germplasm)", required=True, description="候选亲本种质 ID"),
        ParamSpec("target_trait", "string", required=True, description="目标性状（如 耐旱/产量）"),
    ),
    guards=("育种角色权限",),
    post_rules=("亲本合规", "目标性状可预测"),
    writes=("CrossPlan",),
    validate_supported=True,
    hil=HilPolicy(reviewer_role="育种专家",
                  predicate=lambda confidence, touched_hard: confidence < 0.75),
)
def emit_cross_plan(ctx) -> None:
    base, cand, trait = ctx.params["base_id"], ctx.params["candidate_id"], ctx.params["target_trait"]
    gain = ctx.call_function("杂交预测增益")
    ctx.stage_write("CrossPlan", f"xp_{base}_{cand}", {
        "plan_id": f"xp_{base}_{cand}", "base": base, "candidate": cand,
        "target_trait": trait, "predicted_gain": gain})
    ctx.stage_link("crossed_to", "Germplasm", base, "Germplasm", cand, 目标性状=trait, 预测增益=gain)
    ctx.set_confidence(ctx.params.get("_confidence", 0.82))
    ctx.add_evidence(source="60K 液相基因芯片 GWAS 标记-性状关联")
