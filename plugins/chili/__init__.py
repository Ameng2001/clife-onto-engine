"""辣椒大模型插件（ontology_id = "chili"）—— 第二个行业插件。

存在的唯一目的：证明"换行业零改内核"。它和 grass 用**完全相同**的内核机制
（五要素 / guard / function-backed 规则 / 写后回滚 / 审计 / 参数 schema），
只 import clife_onto_engine.sdk，内核对"辣椒/辣度/品种适配"一无所知。

与 grass 在同一进程的同一 registry 中按 namespace 隔离共存（双本体联邦的最小形态）。
"""
from __future__ import annotations

from pathlib import Path as _Path

from clife_onto_engine.sdk import (
    Backing,
    HilPolicy,
    ObjectType,
    ParamSpec,
    PropertySpec,
    RuleResult,
    Severity,
    spi,
)
from clife_onto_engine.query import InMemoryStore

ONTOLOGY = "chili"

# ---- 槽位 1：Schema（对象声明）------------------------------------------
spi.registry.add_object(ObjectType(
    name="Field", namespace=ONTOLOGY, primary_key="field_id",
    properties=(
        PropertySpec("area_mu", "number", unit="亩", required=True),
        PropertySpec("region", "string", required=True),
        PropertySpec("soil_type", "enum"),
    ),
    states=("draft", "planned", "planting", "harvested"), initial_state="draft",
))
for _ot, _pk in (("PlantingPlan", "plan_id"), ("SeedOrder", "order_id"),
                 ("AdaptListing", "variety"), ("GradeSample", "batch_id")):
    spi.registry.add_object(ObjectType(name=_ot, namespace=ONTOLOGY, primary_key=_pk))


# ---- 槽位 3：guard（declarative）---------------------------------------
@spi.rule(ONTOLOGY, "预算非负", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def budget_non_negative(ctx) -> RuleResult:
    b = ctx.params.get("budget", 0)
    if b is None or b < 0:
        return RuleResult.fail("预算不能为负", suggestion="提供 budget >= 0")
    return RuleResult.ok()


@spi.rule(ONTOLOGY, "种植角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def role_allowed(ctx) -> RuleResult:
    if ctx.actor.role not in {"种植户", "合作社", "农技员"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权制定方案")
    return RuleResult.ok()


@spi.rule(ONTOLOGY, "密度合规", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def density_ok(ctx) -> RuleResult:
    d = ctx.params.get("density")
    if d is None or not (1000 <= d <= 4000):
        return RuleResult.fail("种植密度需在 1000~4000 株/亩", suggestion="调整 density")
    return RuleResult.ok()


# ---- 槽位 3：function-backed Rule（写后，查图谱）-----------------------
@spi.rule(ONTOLOGY, "品种适配", backing=Backing.FUNCTION, severity=Severity.HARD,
          message_template="所选辣椒品种不适配本地，已拦截",
          source="区域辣椒品种适应性区划",
          citations=("NY/T 辣椒生产技术规程", "海南辣椒种植区划报告",))
def variety_adaptation(ctx) -> RuleResult:
    field = ctx.get("Field", ctx.params["field_id"])
    if field is None:
        return RuleResult.fail("地块不存在")
    region = field["region"]
    adapted = {r["variety"] for r in ctx.find("AdaptListing", lambda r: r["region"] == region)}
    plan = ctx.get("PlantingPlan", f"plan_{ctx.params['field_id']}")
    variety = (plan or {}).get("variety")
    if variety not in adapted:
        return RuleResult.fail(f"{region} 不适配品种：{variety}",
                               suggestion=f"改用适配品种：{sorted(adapted)}")
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "制定种植方案",
    description="对一个地块按品种与密度制定辣椒种植方案并下种子订单",
    params=(
        ParamSpec("field_id", "ref(Field)", required=True, description="地块 ID"),
        ParamSpec("variety", "string", required=True, description="辣椒品种名"),
        ParamSpec("density", "number", required=True, description="种植密度（株/亩）"),
        ParamSpec("budget", "number", required=False, description="预算（元/亩）"),
    ),
    guards=("预算非负", "种植角色权限", "密度合规"),
    post_rules=("品种适配",),
    writes=("PlantingPlan", "SeedOrder"),
    validate_supported=True,
    hil=HilPolicy(reviewer_role="农技审核员",
                  predicate=lambda confidence, touched_hard: confidence < 0.75),
)
def make_planting_plan(ctx) -> None:
    fid = ctx.params["field_id"]
    variety = ctx.params["variety"]
    density = ctx.params["density"]
    ctx.stage_write("PlantingPlan", f"plan_{fid}", {"field_id": fid, "variety": variety, "density": density})
    ctx.stage_write("SeedOrder", f"so_{fid}", {"field_id": fid, "variety": variety, "qty_per_mu": density})
    ctx.emit_effect("workitem", on="accepted", template="辣椒种植作业工单", field_id=fid)
    ctx.set_confidence(ctx.params.get("_confidence", 0.85))
    ctx.add_evidence(standard="NY/T 辣椒生产技术规程")


def seed_reference_data(store: InMemoryStore) -> None:
    store.put_object("Field", "field_001", {
        "field_id": "field_001", "area_mu": 30, "region": "海南", "soil_type": "砂壤",
    })
    for v in ("朝天椒", "黄灯笼椒", "海椒1号"):
        store.put_object("AdaptListing", f"海南::{v}", {"region": "海南", "variety": v})


# 第二个 Action 闭环：辣椒分级。import 即注册。
from . import grading  # noqa: E402,F401

# 槽位 2：物理映射
spi.load_mappings(ONTOLOGY, _Path(__file__).parent / "mappings" / "objects.yaml")
