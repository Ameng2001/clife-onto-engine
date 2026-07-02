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
from clife_onto_engine.query import InMemoryStore, StagedLink

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
# 后端 bootstrap 据此建 TAG。查询相关对象声明字段，供意图编译器的能力清单暴露给 LLM。
spi.registry.add_object(ObjectType(name="Degradation", namespace=ONTOLOGY, primary_key="deg_id",
    properties=(PropertySpec("level", "string"), PropertySpec("type", "string"))))
spi.registry.add_object(ObjectType(name="RestorationMethod", namespace=ONTOLOGY, primary_key="method_id",
    properties=(PropertySpec("name", "string"),)))
spi.registry.add_object(ObjectType(name="SeedPack", namespace=ONTOLOGY, primary_key="pack_id",
    properties=(PropertySpec("name", "string"),)))
# GrassSpecies（对齐方案 §5.4 #1）：承载"播量∈区间"校验的数据源（seeding_rate_min/max）。
spi.registry.add_object(ObjectType(name="GrassSpecies", namespace=ONTOLOGY, primary_key="species",
    properties=(
        PropertySpec("seeding_rate_min", "number", unit="kg/亩"),
        PropertySpec("seeding_rate_max", "number", unit="kg/亩"),
        PropertySpec("native", "bool"),
        PropertySpec("adapts_to", "list"),   # 适配的立地类型（§5.5 #1）：立地适配校验数据源
    )))
for _ot, _pk in (("Project", "site_id"), ("ForageSample", "batch_id"), ("NativeListing", "species")):
    spi.registry.add_object(ObjectType(name=_ot, namespace=ONTOLOGY, primary_key=_pk))

spi.registry.add_link(LinkType("suffers", ONTOLOGY, "Site", "Degradation",
                               edge_semantics=EdgeSemantics.HYPOTHESIS))
spi.registry.add_link(LinkType("treated_by", ONTOLOGY, "Degradation", "RestorationMethod",
                               edge_semantics=EdgeSemantics.DERIVATION))
spi.registry.add_link(LinkType("uses", ONTOLOGY, "RestorationMethod", "SeedPack",
                               edge_semantics=EdgeSemantics.DERIVATION))
# composed_of（方案 §5.5 #13）：种子包→草种，属性携带混播比例与播量，供"混播配比合规"校验。
spi.registry.add_link(LinkType("composed_of", ONTOLOGY, "SeedPack", "GrassSpecies",
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


@spi.rule(
    ONTOLOGY, "混播配比合规", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="种子包配比/播量不合规，已拦截",
    source="草种混播配比规则 + 品种播量区间",
    citations=("DB15/T 草原生态修复技术规程", "GB/T 37067 退化草地修复技术规范"),
)
def seedpack_composition_valid(ctx) -> RuleResult:
    """混播 Σ比例=100% ∧ 每草种播量∈GrassSpecies 区间。

    仅当种子包带结构化 composition 时校验；legacy 的纯 species 输入不触发（向后兼容）。
    """
    sp = ctx.get("SeedPack", f"sp_{ctx.params['site_id']}") or {}
    comp = sp.get("composition")
    if not comp:                       # 无结构化配比 → 不校验（兼容 species-only）
        return RuleResult.ok()
    total = sum(c.get("ratio", 0) for c in comp)
    if round(total, 3) != 100:
        return RuleResult.fail(f"混播比例合计 {total}% ≠ 100%",
                               suggestion="调整各草种比例使合计=100%")
    for c in comp:
        gs = ctx.get("GrassSpecies", c["species"]) or {}
        lo, hi, sr = gs.get("seeding_rate_min"), gs.get("seeding_rate_max"), c.get("seeding_rate")
        if lo is not None and hi is not None and sr is not None and not (lo <= sr <= hi):
            return RuleResult.fail(
                f"{c['species']} 播量 {sr} 超出区间 [{lo},{hi}] kg/亩",
                suggestion=f"{c['species']} 播量应∈[{lo},{hi}] kg/亩")
    return RuleResult.ok()


@spi.rule(
    ONTOLOGY, "立地适配", backing=Backing.FUNCTION, severity=Severity.HARD,
    message_template="草种与地块立地类型不适配，已拦截",
    source="草种立地适应性 adapts_to（乡土 ≠ 立地适配，独立于乡土合规）",
    citations=("GB/T 37067 退化草地修复技术规范",),
)
def site_type_adaptation(ctx) -> RuleResult:
    """每草种须适配地块立地类型（如盐碱地只用耐盐碱草种）。

    与「乡土合规」是两道独立闸：草种可能是本盟市乡土、却不适配这块地的立地。
    仅当带结构化 composition 且草种/地块有 adapts_to/site_type 数据时校验。
    """
    sp = ctx.get("SeedPack", f"sp_{ctx.params['site_id']}") or {}
    comp = sp.get("composition")
    if not comp:
        return RuleResult.ok()
    st = (ctx.get("Site", ctx.params["site_id"]) or {}).get("site_type")
    if not st:
        return RuleResult.ok()             # 立地未知 → 不在此拦
    bad = []
    for c in comp:
        adapts = (ctx.get("GrassSpecies", c["species"]) or {}).get("adapts_to") or []
        if adapts and st not in adapts:    # 有适配数据且不含本立地 → 判不适配
            bad.append(c["species"])
    if bad:
        return RuleResult.fail(f"草种 {bad} 不适配立地「{st}」",
                               suggestion=f"改用适配「{st}」的乡土草种")
    return RuleResult.ok()


# ---- 槽位 4：Action -----------------------------------------------------
@spi.action(
    ONTOLOGY, "出一地一方",
    description="对一个退化地块生成修复方案（种子包+造价）并派单",
    params=(
        ParamSpec("site_id", "ref(Site)", required=True, description="地块/草场 ID"),
        ParamSpec("species", "list", required=True, description="拟用草种名列表"),
        ParamSpec("composition", "list", required=False,
                  description="结构化混播配比 [{species, ratio(%), seeding_rate(kg/亩)}]；提供则校验配比/播量"),
        ParamSpec("method", "ref(RestorationMethod)", required=False,
                  description="选用的修复方法 ID；提供则连 uses→种子包，贯通修复链"),
        ParamSpec("budget", "number", required=False, description="预算（元/亩）"),
    ),
    guards=("预算非负", "角色权限"),
    post_rules=("乡土合规", "混播配比合规", "立地适配"),
    writes=("Project", "SeedPack"),
    validate_supported=True,
    hil=HilPolicy(
        reviewer_role="乡土草种合规官",
        predicate=lambda confidence, touched_hard: confidence < 0.75,
    ),
)
def emit_restoration_plan(ctx) -> None:
    site_id = ctx.params["site_id"]
    comp = ctx.params.get("composition")
    # composition 提供时为权威：派生 species 供乡土合规，并写 composed_of 边供配比/播量校验
    species = [c["species"] for c in comp] if comp else ctx.params["species"]
    pack = {"species": species, "site_id": site_id}
    if comp:
        pack["composition"] = comp
    # 内存变更：暂存 SeedPack 与 Project（进 live index，写后规则立即可见）
    ctx.stage_write("SeedPack", f"sp_{site_id}", pack)
    for c in (comp or ()):
        ctx.stage_link("composed_of", "SeedPack", f"sp_{site_id}", "GrassSpecies", c["species"],
                       ratio=c.get("ratio"), seeding_rate=c.get("seeding_rate"))
    # 修复方法用该种子包（uses）：贯通"退化→方法→种子包→草种"修复链
    method = ctx.params.get("method")
    if method:
        ctx.stage_link("uses", "RestorationMethod", method, "SeedPack", f"sp_{site_id}")
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
    # GrassSpecies 播量区间 + 立地适配（demo 值）：供「混播配比合规」「立地适配」校验。
    # 披碱草：巴彦淖尔乡土、但只适配沙地/草原（不耐盐碱）→ 演示乡土 ≠ 立地适配。
    for _sp, _lo, _hi, _ad in (("碱茅", 1.0, 2.5, ["盐碱", "沙地"]),
                               ("星星草", 0.8, 2.0, ["盐碱"]),
                               ("披碱草", 1.5, 3.0, ["沙地", "草原"])):
        store.put_object("GrassSpecies", _sp, {"species": _sp, "seeding_rate_min": _lo,
                                               "seeding_rate_max": _hi, "native": True, "adapts_to": _ad})

    # 品质子图参考数据：标准 + 一条已评级样本，供"评级挂到依据标准"多跳查询验收。
    store.put_object("Standard", "NY/T 1574",
                     {"std_id": "NY/T 1574", "name": "苜蓿干草质量分级", "version": "2007"})
    store.put_object("ForageSample", "batch_demo", {"batch_id": "batch_demo", "RFV": 140})
    store.put_object("QualityIndex", "qi_batch_demo",
                     {"qi_id": "qi_batch_demo", "batch_id": "batch_demo", "RFV": 140, "grade": "一级"})
    store.put_link(StagedLink(link_type="has_quality", from_type="ForageSample", from_key="batch_demo",
                              to_type="QualityIndex", to_key="qi_batch_demo", props={"等级": "一级"}))
    store.put_link(StagedLink(link_type="measured_by", from_type="QualityIndex", from_key="qi_batch_demo",
                              to_type="Standard", to_key="NY/T 1574", props={"方法": "RFV分级"}))


# 第二个 Action 闭环：草易·快检评级。import 即完成 SPI 注册。
from . import forage  # noqa: E402,F401

# Phase 1：6 大子图 schema 层贯通（育种/碳汇/监测等对象与关系；schema-only）。
from . import subgraphs  # noqa: E402,F401

# 槽位 2：加载对象/关系物理映射（声明式 YAML）。
spi.load_mappings(ONTOLOGY, _Path(__file__).parent / "mappings" / "objects.yaml")
