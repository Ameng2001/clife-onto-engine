"""草业插件（ontology_id = "grass"）—— tenant-zero，验证内核接缝是否干净。

它**只** import `clife_onto_engine.sdk`，用元模型五要素声明草业本体；
内核对"草种/乡土合规/载畜量"一无所知。若本插件被迫去改内核才能跑通，
即说明接缝划错——修内核，而非在此打补丁。

最小集：1 个 Object（Site）+ 1 个 guard + 1 个 function-backed Rule（乡土合规）
+ 1 个 Action（出一地一方）。足以走通 guard→变更→写后校验→回滚/提交→审计全链路。
"""
from __future__ import annotations

from pathlib import Path as _Path

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
from clife_onto_engine.query import InMemoryStore

ONTOLOGY = "grass"

# ---- 槽位 1：Schema（对象声明）------------------------------------------
spi.registry.add_object(ObjectType(
    name="Site", namespace=ONTOLOGY, primary_key="parcel_id",
    properties=(
        PropertySpec("area_mu", "number", unit="亩", required=True),
        PropertySpec("region", "string", required=True),
        PropertySpec("site_type", "enum"),
    ),
    states=("draft", "surveyed", "treating", "accepted"), initial_state="draft",
))

# 修复推理主干涉及的对象与关系（供 OQL / Search Around 导航）；
# Action 写入对象（Project/SeedPack/ForageSample）与参考数据对象（NativeListing）也在此声明，
# 后端 bootstrap 据此建 TAG。
for _ot, _pk in (
    ("Degradation", "deg_id"), ("RestorationMethod", "method_id"), ("SeedPack", "pack_id"),
    ("Project", "site_id"), ("ForageSample", "batch_id"), ("NativeListing", "species"),
):
    spi.registry.add_object(ObjectType(name=_ot, namespace=ONTOLOGY, primary_key=_pk))

spi.registry.add_link(LinkType("suffers", ONTOLOGY, "Site", "Degradation",
                               edge_semantics=EdgeSemantics.HYPOTHESIS))
spi.registry.add_link(LinkType("treated_by", ONTOLOGY, "Degradation", "RestorationMethod",
                               edge_semantics=EdgeSemantics.DERIVATION))
spi.registry.add_link(LinkType("uses", ONTOLOGY, "RestorationMethod", "SeedPack",
                               edge_semantics=EdgeSemantics.DERIVATION))


# ---- 槽位 3：guard（declarative，写入前）---------------------------------
@spi.rule(ONTOLOGY, "预算非负", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def budget_non_negative(ctx) -> RuleResult:
    budget = ctx.params.get("budget", 0)
    if budget is None or budget < 0:
        return RuleResult.fail("预算不能为负", suggestion="提供 budget >= 0")
    return RuleResult.ok()


@spi.rule(ONTOLOGY, "角色权限", backing=Backing.DECLARATIVE, severity=Severity.HARD)
def role_allowed(ctx) -> RuleResult:
    if ctx.actor.role not in {"施工方", "牧民", "监管"}:
        return RuleResult.fail(f"角色 {ctx.actor.role} 无权出方案")
    return RuleResult.ok()


# ---- 槽位 3：function-backed Rule（写后，查图谱）-------------------------
@spi.rule(
    ONTOLOGY, "乡土合规", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="种子包含非乡土草种，已拦截",
    source="蒙草乡土草种名录 + 草原生态修复乡土性要求",
    citations=("GB/T 37067 退化草地修复技术规范", "DB15/T 草原生态修复技术规程"),
)
def native_species_compliance(ctx) -> RuleResult:
    # 读本次暂存的 SeedPack（写即可见）+ 地块所在盟市的乡土名录
    site = ctx.get("Site", ctx.params["site_id"])
    if site is None:
        return RuleResult.fail("地块不存在")
    region = site["region"]
    allowed = {r["species"] for r in ctx.find("NativeListing", lambda r: r["region"] == region)}
    sp = ctx.get("SeedPack", f"sp_{ctx.params['site_id']}")
    species = (sp or {}).get("species", [])
    illegal = [s for s in species if s not in allowed]
    if illegal:
        return RuleResult.fail(
            f"{region} 乡土名录外草种：{illegal}",
            suggestion=f"改用乡土草种：{sorted(allowed)}",
        )
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "出一地一方",
    description="对一个退化地块生成修复方案（种子包+造价）并派单",
    params=(
        ParamSpec("site_id", "ref(Site)", required=True, description="地块/草场 ID"),
        ParamSpec("species", "list", required=True, description="拟用草种名列表"),
        ParamSpec("budget", "number", required=False, description="预算（元/亩）"),
    ),
    guards=("预算非负", "角色权限"),
    post_rules=("乡土合规",),
    writes=("Project", "SeedPack"),
    validate_supported=True,
    hil=HilPolicy(
        reviewer_role="乡土草种合规官",
        predicate=lambda confidence, touched_hard: confidence < 0.75,
    ),
)
def emit_restoration_plan(ctx) -> None:
    site_id = ctx.params["site_id"]
    species = ctx.params["species"]
    # 内存变更：暂存 SeedPack 与 Project（进 live index，写后规则立即可见）
    ctx.stage_write("SeedPack", f"sp_{site_id}", {"species": species, "site_id": site_id})
    ctx.stage_write("Project", f"proj_{site_id}", {
        "site_id": site_id, "budget": ctx.params.get("budget"), "status": "planned",
    })
    # 副作用声明（commit 后由内核编排）
    ctx.emit_effect("workitem", on="accepted", template="修复施工工单", site_id=site_id)
    # 信任元数据
    ctx.set_confidence(ctx.params.get("_confidence", 0.82))
    ctx.add_evidence(case_id="case_盐碱_001")
    ctx.add_evidence(source="DB15/T-退化分级标准")


def seed_reference_data(store: InMemoryStore) -> None:
    """租户级实例/参考数据（真实落地走 tenants/mengcao 映射注入）。"""
    store.put_object("Site", "parcel_001", {
        "parcel_id": "parcel_001", "area_mu": 500, "region": "巴彦淖尔", "site_type": "盐碱",
    })
    for sp in ("碱茅", "星星草", "披碱草"):
        store.put_object("NativeListing", f"巴彦淖尔::{sp}", {"region": "巴彦淖尔", "species": sp})


# 第二个 Action 闭环：草易·快检评级。import 即完成 SPI 注册。
from . import forage  # noqa: E402,F401

# 槽位 2：加载对象/关系物理映射（声明式 YAML）。
spi.load_mappings(ONTOLOGY, _Path(__file__).parent / "mappings" / "objects.yaml")
