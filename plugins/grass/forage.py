"""草易·AI 快检评级 —— 草业插件的第二个 Action 闭环。

与"出一地一方"形状不同，用来证明同一套内核零改动承载异构动作：
  - 重 Function 派生量：RFV 分级（读暂存草样算等级）
  - 阈值拦截 Rule：霉变超标即 hard 拒绝
  - 产出：等级 + 溯源码 + 溯源凭证副作用

仍只 import clife_onto_engine.sdk，内核对 RFV/霉变一无所知。
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

MOLD_LIMIT = 0.05            # TODO(FDE/专家): demo 值，待换 GB 13078 饲料卫生标准真实限量
REQUIRED = {"CP", "NDF", "ADF", "RFV"}   # 依 NY/T 1574 苜蓿干草分级的必备指标
STD_RFV = "NY/T 1574"       # 苜蓿干草质量分级标准（RFV 分级依据）

# ---- 槽位 1：品质对象层（对齐方案 §5.4 #13/#18、§5.5 #18/#19）------------
# QualityIndex 把 measurements dict 结构化为对象；measured_by 挂到 Standard，
# 使"评级结论有依据、可回查"——落实信任体系"来源可查/结果可验"。
spi.registry.add_object(ObjectType(
    name="QualityIndex", namespace=ONTOLOGY, primary_key="qi_id",
    properties=(
        PropertySpec("batch_id", "string", required=True),
        PropertySpec("RFV", "number"),
        PropertySpec("grade", "string"),
    ),
))
spi.registry.add_object(ObjectType(
    name="Standard", namespace=ONTOLOGY, primary_key="std_id",
    properties=(
        PropertySpec("name", "string"),
        PropertySpec("version", "string"),
    ),
))
spi.registry.add_link(LinkType("has_quality", ONTOLOGY, "ForageSample", "QualityIndex"))
spi.registry.add_link(LinkType("measured_by", ONTOLOGY, "QualityIndex", "Standard"))


# ---- 槽位 3：派生量 Function（只读，算 RFV 等级）------------------------
@spi.function(ONTOLOGY, "RFV分级", reads=("ForageSample",))
def rfv_grade(ctx) -> str:
    # 分级断点来源：美国牧草协会 AFGC RFV 分级 / NY/T 1574（特级≥151…等外<87）。
    # TODO(FDE/专家): 断点值待按采用标准最终核准。
    sample = ctx.get("ForageSample", ctx.params["batch_id"]) or {}
    rfv = sample.get("RFV", 0)
    if rfv >= 151:
        return "特级"
    if rfv >= 125:
        return "一级"
    if rfv >= 103:
        return "二级"
    if rfv >= 87:
        return "三级"
    return "等外"


# ---- 槽位 3：guard（declarative，检测项齐全 + 角色）---------------------
@spi.rule(ONTOLOGY, "检测项完整", backing=Backing.DECLARATIVE, severity=Severity.HARD,
          source="苜蓿干草分级必备检测指标（CP/NDF/ADF/RFV）",
          citations=("NY/T 1574 苜蓿干草质量分级",))
def measurements_complete(ctx) -> RuleResult:
    m = ctx.params.get("measurements", {})
    missing = REQUIRED - set(m)
    if missing:
        return RuleResult.fail(f"缺检测项：{sorted(missing)}", suggestion="补齐 CP/NDF/ADF/RFV")
    return RuleResult.ok()


@spi.rule(ONTOLOGY, "验质角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def grading_role(ctx) -> RuleResult:
    if ctx.actor.role not in {"养殖户", "牧场", "合作社", "施工方"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权评级")
    return RuleResult.ok()


# ---- 槽位 3：function-backed Rule（写后，霉变阈值拦截）------------------
@spi.rule(
    ONTOLOGY, "霉变拦截", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="霉菌毒素超标，禁止评级定价",
    source="饲草霉菌毒素卫生限量（超标不得进入交易）",
    citations=("GB 13078 饲料卫生标准", "NY/T 1574 苜蓿干草卫生要求"),
)
def mold_block(ctx) -> RuleResult:
    sample = ctx.get("ForageSample", ctx.params["batch_id"]) or {}
    toxin = sample.get("霉菌毒素", 0)
    if toxin > MOLD_LIMIT:
        return RuleResult.fail(
            f"霉菌毒素 {toxin} > {MOLD_LIMIT}",
            suggestion="该批次判为不合格，转质检 HIL，不可进入交易",
        )
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "快检评级",
    description="对一批草样按近红外/化验值快检评级并出溯源码",
    params=(
        ParamSpec("batch_id", "string", required=True, description="草样批次号"),
        ParamSpec("measurements", "object", required=True, description="检测值 CP/NDF/ADF/RFV/霉菌毒素 等"),
    ),
    guards=("检测项完整", "验质角色权限"),
    post_rules=("霉变拦截",),
    writes=("ForageSample", "QualityIndex"),
    validate_supported=True,
    hil=HilPolicy(
        reviewer_role="品质定级定价员",
        predicate=lambda confidence, touched_hard: confidence < 0.70,
    ),
)
def quick_test_grading(ctx) -> None:
    batch = ctx.params["batch_id"]
    m = ctx.params["measurements"]
    # 先暂存原始检测值（写即可见，供 Function 与阈值规则读取）
    ctx.stage_write("ForageSample", batch, {**m, "batch_id": batch})
    # 调派生量 Function 算等级
    grade = ctx.call_function("RFV分级")
    # 回写等级 + 溯源码
    ctx.stage_write("ForageSample", batch, {
        **m, "batch_id": batch, "grade": grade, "trace_code": f"TR-{batch}",
    })
    # 结构化品质对象 + 挂依据标准（QualityIndex →measured_by→ Standard）：来源可查、结果可验
    qi_key = f"qi_{batch}"
    ctx.stage_write("QualityIndex", qi_key, {"qi_id": qi_key, "batch_id": batch,
                                             "RFV": m.get("RFV"), "grade": grade})
    ctx.stage_link("has_quality", "ForageSample", batch, "QualityIndex", qi_key, 等级=grade)
    ctx.stage_link("measured_by", "QualityIndex", qi_key, "Standard", STD_RFV, 方法="RFV分级")
    ctx.emit_effect("credential", on="committed", template="溯源凭证", batch_id=batch)
    ctx.set_confidence(m.get("_confidence", 0.88))
    ctx.add_evidence(standard="NY/T 1574 苜蓿干草质量分级")
