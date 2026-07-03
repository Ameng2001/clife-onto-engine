"""草机·作业参数推荐 —— 第五条 Action 闭环（智能装备）。凑齐五智能体。

机手提设备 + 作业类型 + 拟用参数，引擎校验设备支持该作业 + 参数在设备能力域内，出作业工单 +
`operated_by` 关系。与草修/草易/草碳/草育同构。

设计取舍（同 adapts_to/trait_markers 先例）：设备能力用 `params_envelope` **属性**（{参数:[下限,上限]}）
承载而非边——可 JSONL ingest、seed 与 tenant 两路一致。仍只 import clife_onto_engine.sdk。
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

# ---- 槽位 1：装备对象层（对齐方案 §5.4 #23、§5.5 #28）----------------------
spi.registry.add_object(ObjectType(
    name="Equipment", namespace=ONTOLOGY, primary_key="equipment_id",
    properties=(
        PropertySpec("name", "string"),
        PropertySpec("operations", "list"),          # 支持的作业类型（播种/补播/飞防…）
        PropertySpec("params_envelope", "object"),   # {参数: [下限, 上限]}，作业参数能力域
    )))
spi.registry.add_object(ObjectType(
    name="WorkOrder", namespace=ONTOLOGY, primary_key="order_id",
    properties=(PropertySpec("equipment_id", "string"), PropertySpec("operation", "string"),
                PropertySpec("params", "object"))))
spi.registry.add_link(LinkType("operated_by", ONTOLOGY, "WorkOrder", "Equipment"))


# ---- 槽位 3：guard（declarative，角色）-------------------------------------
@spi.rule(ONTOLOGY, "作业角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def operator_role(ctx) -> RuleResult:
    if ctx.actor.role not in {"机手", "施工方", "种植基地"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权下作业工单")
    return RuleResult.ok()


# ---- 槽位 3：function-backed Rule（写后，查设备能力）---------------------
@spi.rule(ONTOLOGY, "设备支持作业", backing=Backing.FUNCTION, severity=Severity.HARD,
          message_template="设备不支持该作业类型，已拦截", source="装备作业能力清单")
def operation_supported(ctx) -> RuleResult:
    eq = ctx.get("Equipment", ctx.params["equipment_id"]) or {}
    if ctx.params["operation"] not in (eq.get("operations") or []):
        return RuleResult.fail(f"设备「{eq.get('name')}」不支持作业「{ctx.params['operation']}」",
                               suggestion=f"该设备支持：{eq.get('operations')}")
    return RuleResult.ok()


@spi.rule(
    ONTOLOGY, "参数在能力域内", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="作业参数超出设备能力域，已拦截",
    source="装备参数能力包络（播深/行距/水肥等）", citations=("装备作业规程/参数手册",),
)
def params_in_envelope(ctx) -> RuleResult:
    env = (ctx.get("Equipment", ctx.params["equipment_id"]) or {}).get("params_envelope") or {}
    for k, v in (ctx.params.get("params") or {}).items():
        rng = env.get(k)
        if rng and not (rng[0] <= v <= rng[1]):
            return RuleResult.fail(f"参数 {k}={v} 超出能力域 [{rng[0]},{rng[1]}]",
                                   suggestion=f"{k} 应∈[{rng[0]},{rng[1]}]")
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "出作业参数",
    description="对设备 + 作业类型 + 拟用参数，校验能力域后出作业工单",
    params=(
        ParamSpec("equipment_id", "ref(Equipment)", required=True, description="作业装备 ID"),
        ParamSpec("operation", "string", required=True, description="作业类型（播种/补播/飞防…）"),
        ParamSpec("params", "object", required=True, description="拟用作业参数 {播深/行距/水肥…}"),
    ),
    guards=("作业角色权限",),
    post_rules=("设备支持作业", "参数在能力域内"),
    writes=("WorkOrder",),
    validate_supported=True,
    hil=HilPolicy(reviewer_role="作业调度员",
                  predicate=lambda confidence, touched_hard: confidence < 0.75),
)
def emit_work_order(ctx) -> None:
    eq, op = ctx.params["equipment_id"], ctx.params["operation"]
    order = f"wo_{eq}_{op}"
    ctx.stage_write("WorkOrder", order, {"order_id": order, "equipment_id": eq,
                                         "operation": op, "params": ctx.params.get("params")})
    ctx.stage_link("operated_by", "WorkOrder", order, "Equipment", eq)
    ctx.emit_effect("workitem", on="committed", template="作业工单派发", equipment_id=eq)
    ctx.set_confidence(ctx.params.get("_confidence", 0.85))
    ctx.add_evidence(source="装备作业规程/参数手册")
