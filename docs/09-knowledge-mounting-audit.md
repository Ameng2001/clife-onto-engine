# 09 · 知识挂载与出处审计（grass · 来源可查落地）

> 对接落地方案（`07`）行动项 4："拉领域专家确认数据口径与规则来源，落实来源可查"。
> 方法：从运行时 registry 抓当前挂载状态（`python -c` introspection / `scripts/smoke_subgraphs.py` 同源），逐条标出缺口与建议补法。
> 原则：**知识不悬空，一律挂在本体要素（对象/规则/动作）上**；每条硬规则、每个分级阈值都要能追到标准号或案例 ID，否则"来源可查/结果可验"不成立。

---

## 一、已挂载知识清单（现状）

### 1.1 规则挂的知识（RuleDef.source / citations）

| 规则 | 类型 | source | citations | 出处状态 |
|---|---|---|---|---|
| 乡土合规 | function/hard | 蒙草乡土草种名录 + 乡土性要求 | GB/T 37067、DB15/T 修复规程 | ✅ 齐 |
| 混播配比合规 | function/hard | 草种混播配比规则 + 品种播量区间 | DB15/T、GB/T 37067 | ✅ 齐 |
| 立地适配 | function/hard | 草种立地适应性 adapts_to | GB/T 37067 | ✅ 齐 |
| 霉变拦截 | function/hard | 饲草霉菌毒素卫生限量 | GB 13078 饲料卫生标准、NY/T 1574 卫生要求 | ✅ 已补（本轮） |
| 检测项完整 | declarative/hard | 苜蓿干草分级必备指标 | NY/T 1574 | ✅ 已补（本轮） |
| 验质角色权限 | declarative/hard | （空） | （空） | 🟢 策略性 guard，出处可选 |
| 角色权限 | declarative/hard | （空） | （空） | 🟢 同上 |
| 预算非负 | declarative/hard | （空） | （空） | 🟢 同上 |

### 1.2 对象挂的附着知识（mappings `knowledge:`）

| 对象 | kind | 名称 | refs |
|---|---|---|---|
| Degradation | diagnostic | 盐碱化常见成因 | DB15/T 修复规程 |
| Degradation | playbook | 退化分级处置手册 | （无） |
| RestorationMethod | reference | 方法适用性参考 | GB/T 37067 |
| Site | template | 地块修复评估模板 | （无） |

**覆盖：26 对象中 8 个挂了附着知识**——原 3 个（Site/Degradation/RestorationMethod）+ P1 本轮补的 5 个活跃闭环对象：

| 对象 | kind | 名称 |
|---|---|---|
| GrassSpecies | reference | 乡土草种选种要点 |
| SeedPack | playbook | 混播组合设计手册 |
| QualityIndex | diagnostic | CP/NDF/ADF/RFV 判读 |
| Standard | reference | NY/T 1574 分级条款摘要 |
| ForageSample | template | 快检取样与近红外规范 |

### 1.3 派生量 Function

| Function | reads | 阈值出处 |
|---|---|---|
| RFV分级 | ForageSample | 分级断点 151/125/103/87 硬编码，运行时经 `add_evidence(standard="NY/T 1574")` 留痕，但断点本身未在代码注明来源 |

---

## 二、缺口分级与建议补法

### P0 · 硬规则/阈值出处

**已补（本轮·代码坐实）**：
- ✅ **霉变拦截** rule — 补 `source` + `citations`(GB 13078、NY/T 1574)；
- ✅ **检测项完整** rule — 补 `source` + `citations`(NY/T 1574)；
- ✅ **RFV 分级断点** / **MOLD_LIMIT** — 代码注明来源(AFGC/NY/T 1574、GB 13078)并标 `TODO(FDE/专家)` 待核准。
- 结果：**所有 function/hard 规则出处全覆盖**（`introspection` 校验 0 缺）。

**🔴 仍待专家（demo 值 → 真实值，规则逻辑已就位、只等换数）**：

| 项 | 现状 | 待专家给 |
|---|---|---|
| 霉菌毒素限量 `MOLD_LIMIT` | demo 0.05 | GB 13078 真实限量 |
| RFV 分级断点 | demo 151/125/103/87 | 采用标准的确切断点 |
| **播量区间** seeding_rate | 碱茅[1.0,2.5] 等 demo | 真实品种播种技术规程值 |
| **立地适配** adapts_to | 碱茅→盐碱/沙地 等 demo | 蒙草案例库/研究核准 + 案例 ID |

### ✅ P1 · 活跃闭环对象附着知识（本轮已补）

两条闭环的 5 个活跃对象已挂附着知识（GrassSpecies/SeedPack/QualityIndex/Standard/ForageSample），随对象在 Explorer 一次呈现、载入 Agent 记忆。详见 §1.2 表。

### 🟢 P2 · 可暂缓

- **策略性 guard**（角色权限/验质角色权限/预算非负）：属权限/参数校验，非领域知识，出处可选。
- **子图 4/5/6 空骨架对象**（Germplasm/CarbonParcel/MonitorObs 等 16 个）：schema-only，附着知识随各自闭环上线时补，现在不补是对的（避免堆无用知识）。

---

## 三、待专家确认的口径/阈值汇总（行动项 4 的输入清单）

给领域专家一张可直接勾选的表：

| # | 待确认项 | 当前 demo 值 | 需专家给 | 落点 |
|---|---|---|---|---|
| 1 | 霉菌毒素限量 | 0.05 | 真实限量 + 标准号 | forage.py `MOLD_LIMIT` + 霉变拦截 citations |
| 2 | RFV 分级断点 | 151/125/103/87 | 采用的分级标准 | forage.py `rfv_grade` + Standard 数据 |
| 3 | 各草种播量区间 | 碱茅[1.0,2.5]… | 真实播量区间 | grass_species.csv `seeding_rate_min/max` |
| 4 | 草种立地适应 | 碱茅→盐碱/沙地… | 真实适应立地 + 案例 | grass_species.csv `adapts_to` |
| 5 | 乡土名录 | 巴彦淖尔 5 种 | 各盟市完整名录 | native_listings.csv |
| 6 | 检测必备项 | CP/NDF/ADF/RFV | 依标准的完整指标集 | forage.py `REQUIRED` + 检测项完整 citations |

---

## 四、自检命令

```bash
# 规则出处 + 对象附着知识现状（本文件数据来源）
python -c "import plugins.grass; from clife_onto_engine.sdk import spi; ..."
# 结构缺口（悬空引用/缺 handler）
python scripts/smoke_gaps.py
# OKF 导出（citations 进知识包，供人读核对）
```

> 补齐 P0 后，本体的"来源可查"才从 3/8 规则达到全覆盖；P1 让 Agent 推理有据；P2 随闭环增量。这份清单即行动项 4 与专家对齐的工作底稿。
