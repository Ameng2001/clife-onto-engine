# 08 · Phase 0 · 两条闭环最小对象/规则清单（落地 spec）

> 落地方案（`07-wencao-ontology-delivery-plan.md` §8）行动项 3 的产出。
> 目标：把 `plugins/grass` 现有 **demo 骨架**补成"能用真实蒙草数据跑通"的**最小真闭环**，2–3 周（Phase 0 冷启）内完成，CQ 全绿。
> 纪律：只补两条闭环 CQ 需要的对象/规则，**不铺全量 25 实体**；退化分级 ML、施工窗口、数仓聚合面一律后置。

---

## 0. 基线现状（已跑通，勿重造）

`python scripts/smoke_cq.py` → **CQ 4/4 通过**，且版本削弱规则被验收门抓住。现有资产：

| 闭环 | 已有对象 | 已有关系 | 已有规则/Function | Action | CQ |
|---|---|---|---|---|---|
| **A 草修·出一地一方** | Site（全）、Degradation、RestorationMethod、SeedPack、Project、NativeListing | suffers、treated_by、uses | guard 预算非负 / 角色权限；**乡土合规**(function-backed) | 出一地一方 | 3 action + 1 query ✅ |
| **B 草易·快检评级** | ForageSample | — | **RFV分级**(function)；检测项完整 / 验质角色权限；**霉变拦截** | 快检评级 | **无 ❌** |

**demo 的短板**（Phase 0 要补的）：
- A：`SeedPack` 只存草种列表，**没有配比/播量** → "混播 Σ=100%""播量∈区间""立地适配"三条规则**无数据可校**；`GrassSpecies`/`Material` 未建模。
- B：`QualityIndex`/`Standard` 未建模，评级结论**未挂依据标准**（"来源可查"不完整）；**无 CQ 套件**。

---

## 1. Phase 0 目标最小集（对齐方案 §5.4/§5.5，只取两条闭环所需）

**对象（9 类）**：`Site` `SiteType` `Region` `Degradation` `RestorationMethod` `SeedPack` `GrassSpecies` `Material` `NativeListing`（A）+ `ForageSample` `QualityIndex` `Standard`（B）。
> 注：`Project` 作为 Action 写入对象保留；`Livestock`/`Ration`（日粮）**后置到 P1**。

**关系（8 类）**：`located_in` `has_site_type` `suffers` `treated_by` `uses` `composed_of` `contains_material` `adapts_to`（A）+ `has_quality` `measured_by`（B）。

---

## 2. 增量清单（Δ：基线 → Phase 0）

### 闭环 A · 草修·出一地一方

| # | 增量 | 类型 | 说明 / 对齐方案 | 关键点 |
|---|---|---|---|---|
| A1 | `GrassSpecies` 对象 | 对象 | §5.4 #1。属性：name、life_form、seeding_rate_min/max（播量区间）、native(bool) | 承载"播量∈区间"校验的数据源 |
| A2 | `Material` 对象 | 对象 | §5.4 #11。改良剂/菌剂/保水剂 + 用量 | 种子包含料校验 |
| A3 | `SiteType`/`Region` 提升为对象 | 对象 | §5.4 #7/#25。现为 Site 的 enum/string 字段 | 支撑 `adapts_to`/`located_in` 导航 |
| A4 | `composed_of`（SeedPack→GrassSpecies，属性 ratio、seeding_rate） | 关系 | §5.5 #13。**最关键补齐** | 无它则配比/播量规则空转 |
| A5 | `contains_material`（SeedPack→Material，属性 dosage） | 关系 | §5.5 #14 | — |
| A6 | `adapts_to`（GrassSpecies→SiteType，属性 适应度、播量） | 关系 | §5.5 #1 | 支撑"立地适配"规则 |
| A7 | `has_site_type` / `located_in` | 关系 | §5.5 #9/#8 | 导航 + 乡土合规按 region 取名录（现已隐式用 region 字段） |
| A8 | **混播配比合规** Rule（function-backed, HARD） | 规则 | §5.8。Σ(ratio)=100% ∧ 每草种 seeding_rate∈[min,max] | 读暂存 SeedPack 的 composed_of |
| A9 | **立地适配** Rule（function-backed, HARD） | 规则 | §5.8。每草种 adapts_to 覆盖该 Site 的 site_type | 与"乡土合规"并列为选型双闸 |
| A10 | `出一地一方` Action 参数升级 | Action | params 增 `composition`（[{species, ratio, seeding_rate}]）；写入 composed_of | 承接 A4/A8/A9 |

> **不做（P0 明确后置）**：`退化分级判定`（需遥感+样方 ML → P1.5，P0 直接消费已 ingest 的 `Degradation.level`）；`施工窗口 constrained_by`（需气象 → P1.5）；`applied_in`/`achieves` 历史成效（需案例回写 → P1）。

### 闭环 B · 草易·快检评级

| # | 增量 | 类型 | 说明 / 对齐方案 | 关键点 |
|---|---|---|---|---|
| B1 | `QualityIndex` 对象 | 对象 | §5.4 #13。CP/NDF/ADF/RFV/水分/霉菌毒素 + 等级 | 把 measurements dict 结构化为对象 |
| B2 | `Standard` 对象 | 对象 | §5.4 #18。标准号、阈值条款、版本（NY/T 1574 等） | "结果可验/来源可查" |
| B3 | `has_quality`（Forage/ForageSample→QualityIndex）/ `measured_by`（QualityIndex→Standard） | 关系 | §5.5 #18/#19 | 评级结论挂依据标准 |
| B4 | **掺杂/水分阈值** Rule（可选, function-backed） | 规则 | §5.8。水分/杂质越阈转 HIL | 与"霉变拦截"同形，按需 |
| B5 | **forage CQ 套件** | CQ | 补 §7 槽位 | **必做**（见 §3.2） |

---

## 3. CQ 验收（Phase 0 完成判定）

### 3.1 闭环 A 新增 CQ（在现 4 条基础上补）

- **配比不足 100% 被拦**：`出一地一方` composition=[{碱茅,0.6},{星星草,0.3}] → expect reject·混播配比合规
- **播量越区间被拦**：某草种 seeding_rate 超出 GrassSpecies 区间 → expect reject·混播配比合规
- **立地不适配被拦**：草种 adapts_to 不含该 Site 的 site_type → expect reject·立地适配
- **完整合规出方案（commit）**：乡土 ∧ Σ=100% ∧ 播量合规 ∧ 立地适配 → expect commit

### 3.2 闭环 B 新增 CQ（当前为 0，全新）

- **合规草样出等级（commit）**：measurements 齐全 ∧ 霉变达标 → expect commit，且 grade 命中 RFV 分级
- **缺检测项被拦**：missing CP → expect reject·检测项完整
- **霉变超标被拦**：霉菌毒素 > 阈值 → expect reject·霉变拦截
- **越权角色被拦**：actor_role=游客 → expect reject·验质角色权限
- **等级挂到依据标准（query）**：QualityIndex →measured_by→ Standard 查得到 NY/T 1574

> 验收门槛：`python scripts/smoke_cq.py` 扩到覆盖 A（8 条）+ B（4 条）全绿；且"去规则版本"能被 change-impact 抓到回归（沿用现有回路）。

**落地状态（已完成，12/12 全绿 · seed 与真实 tenant 两路一致）**：
- 闭环 A（8 条）：合规草种出方案、非乡土草种被拦、越权角色被拦、合规配比出方案、配比不足被拦、播量越界被拦、乡土但立地不适配被拦、某区域有地块(query)。四道治理闸齐：`乡土合规` + `混播配比合规`(Σ=100% ∧ 播量∈区间) + `立地适配`，加 guard(预算/角色)。
- 闭环 B（4 条）：合规草样出评级、霉变草样被拦、缺检测项被拦、越权角色评级被拦。三道闸齐：`检测项完整` + `霉变拦截` + `验质角色权限`，评级结论经 QualityIndex→measured_by→Standard 挂依据标准。
- B 原计划 5 条中的"等级挂到依据标准(query)"按 §3.3 撤下——commit CQ 已 robust 验证挂标准接线，无需脆弱的预置图实例断言。

### 3.3 CQ 设计经验（B1–B3 落地时踩到，须遵守）

**CQ 应断言"对真实 tenant 数据成立的能力"，而非预置的演示实例。** B1–B3 曾加过一条多跳 QueryCQ「评级挂到依据标准」（`ForageSample→has_quality→QualityIndex→measured_by→Standard`），在 `seed_reference_data` 下通过，却在 `load_tenant(MENGCAO)` 真实数据下 **0 行失败**——因为 `QualityIndex`/关系是 **Action 运行时产生、不是 ingest 进来的**，用预置图实例去断言是"脆弱 CQ"。

**正确姿势**：验证"Action 会写某对象/关系"用 **ActionCQ 的 commit**——`validate` 干跑会真的执行 handler 的 `stage_write`/`stage_link`，若对象/关系/`writes` 未声明会抛 `CapabilityError` 使 CQ 失败；**commit 通过即证明接线正确**，且该断言对 seed 与真实 tenant 数据都成立。仅当断言的图实例来自 **ingest 的真实数据**（如「某区域有地块」依赖 tenant 的 Site）时才用 QueryCQ。

---

## 4. 真实数据接入（tenants/mengcao）

Phase 0 的数据经 `tenant/ingest` 声明式落库（现有 `tenants/mengcao/` sample CSV 为模板），至少补三张：

| 对象 | 来源 | 口径（须专家确认 source/citations） |
|---|---|---|
| `NativeListing` / `GrassSpecies` | 蒙草乡土草种名录 + 审定名录 | 按盟市的乡土性、播量区间、立地适应（碱茅/星星草/披碱草…） |
| `GrassSpecies -adapts_to- SiteType` | 修复案例 + 标准 | 盐碱/沙地/矿山各立地的适配草种与适应度 |
| `ForageSample` + `Standard` | 快检记录 + NY/T 1574 | RFV 分级阈值、霉菌毒素限值 |

> 数据口径与规则来源是"来源可查"的落点——每条乡土名录/分级阈值都要能追到标准号或案例 ID（对应行动项 4，需拉领域专家）。

---

## 5. Phase 0 排期（2–3 周）

| 周 | 任务 | 产出 |
|---|---|---|
| W1 | A1–A7 对象/关系补齐 + tenants/mengcao 数据接入（乡土名录/GrassSpecies/adapts_to） | schema 扩展 + 真数据落库、IngestReport 绿 |
| W2 | A8–A10 配比/播量/立地规则 + Action 升级；B1–B4 QualityIndex/Standard/关系 | 两条闭环 function-backed 规则跑通 |
| W3 | 3.1 + 3.2 CQ 套件补全并全绿；Explorer 演示两条闭环"过程可溯"；评审附录 | `smoke_cq.py` A8+B5 全通过、可演示 |

---

## 6. 与落地方案的衔接

- 本 spec = 方案 §4.12.10 "一期：6 子图贯通 + 两个 Action 闭环"的 **Phase 0 打底**（先把 2 闭环做真，6 子图 schema 层在 P1 补齐）。
- `studio-ontology` `map→compile` 可先起 A1–A3/B1–B2 的对象骨架，function-rule 体（A8/A9/B4）与 Action 升级仍需 FDE 手填（`TODO(FDE)`）。
- 后置项（退化分级 ML、施工窗口、日粮、数仓聚合）在 P1/P1.5 按用例牵引接入，均以 Action/Function 挂到已建对象上，**不改内核**。
