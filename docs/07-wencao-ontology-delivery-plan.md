# 07 · 问草大模型 2.0 · 本体部分整体落地方案与计划

> 范围：内蒙古草业集团《问草大模型 2.0》建设方案第四章（草业数智本体）+ 第五章（草业知识图谱）的**工程落地**。
> 视角：FDE（前置交付工程）——以最短路径把"信任内核 + 两条业务闭环"交付到 2026.07 首发，其余按用例牵引增量补齐。
> 依据：`clife-onto-engine`（运行时，本仓库）+ `astra-studio-plugins/studio-ontology`（建模端）当前实现进展。

---

## 0. 一句话结论

本体部分**可行，且是全方案可行性最高的一块**：方案反复强调的"来源可查 / 过程可溯 / 结果可验、写入治理、双层校验、防幻觉在执行层"——在引擎里几乎能逐条对上**已实现且离线重度测过**的模块。真正的工作量不在架构，在**内容工程**（把实体/关系/规则用真实蒙草数据填进去）与几块**规模化适配**。

关键纪律：**本体运行时交付 ≠ 本体大模型训练**。方案第六章把两者耦合叙述，工程上必须切割——运行时现在就能交付并拿标杆，权重内化训练是 2027 增强，不得绑架首发。

---

## 1. 现状盘点（引擎 ↔ 方案对齐）

### 1.1 已具备、可直接复用（🟢 信任内核）

| 方案主张（Ch4/5） | 引擎落点 | 状态 |
|---|---|---|
| 本体三层 对象/逻辑/动作（§4.2） | 五要素元模型 `metamodel.py`：Object / Function+Rule / Action | ✅ CI 强制内核纯净 |
| 两层 Plan（§4.3） | `intent/compiler.py` + `kernel/action_engine.py` | 🟢 执行层跑通；语义层靠 manifest+OQL 兜底 |
| 防幻觉在执行层、OAG（§4.12.6） | 意图编译仅在能力清单内提议，内核确定性校验，越权 reject | ✅ 真 Qwen 抽检 14/14、对抗 0 不安全落库 |
| 写入治理 Funnel / Action 一等契约（§4.12.7） | `action_engine.execute()`：authz→guard→沙箱→post-rule 不短路→原子 flush+补偿回滚→审计→HIL | ✅ **最成熟**，production-grade |
| 双层校验 声明式+Function-backed（§4.12.7③） | 声明式 guard + function-backed rule（乡土合规已 demo） | ✅ 已实现 |
| Search Around / 受限 OQL DSL / 算子计费（§4.12.8） | `query/oql.py`：结构化 AST、schema 校验防注入、多跳、`CostMeter` | 🟢 原型完整（缺 OR/排序，`to_ngql` 仅示意） |
| 映射注册表（§4.6/4.8） | `sdk/mapping.py` + `mappings/objects.yaml` | ✅ 声明式 YAML |
| CQ 验证（§4.7） | `cq.py` + `plugins/grass/cq.py` | 🟢 引擎+grass 有 |
| 版本治理 / 决策回放（§4.7） | `versioning.py` / `replay.py` / `change_impact.py` | ✅ 已实现 |
| 分层权限 + Purpose（§4.12.8③） | `authz.py` / `identity.py` / tenant boundary | 🟢 对象/角色级有 |
| 声明式租户入数（§4.6） | `tenant/ingest.py` + `tenants/mengcao/`（含 sample CSV） | ✅ 可审计 IngestReport |

> 起点不是零：`plugins/grass` 已把"草修·出一地一方 + 草易·快检评级"两条闭环 demo 出来（8 对象 / 3 关系 / 2 guard / 乡土合规 function-rule / Action / 快检评级）。

### 1.2 需工程补齐（🟡 有确定路径）

- NebulaGraph 生产适配（schemaless JSON 列 → 原生列）+ 真集群压测至千万级三元组；
- **向量库 + 知识检索**（Milvus/pgvector）——引擎目前无；
- 遥测读从"只产计划"扩到**数仓/分析面**（见 §3.2）；
- real-Qwen / real-Nebula 从手工抽检进 CI；
- tenant schema YAML 化、`plugin.yaml` manifest 加载器、slots 5/6（每插件记忆词典 + agent 角色）；
- 三范式训练集导出器（OKF 读层已有）。

### 1.3 不在"本体交付"范围（🔴 显式切割，独立立项）

- 问草本体大模型训练（CPT/SFT/RLHF 权重内化，§6.2）；
- 22 个 ML 模型（GS 育种 / 快检 CNN / 遥感反演，§6.5）；
- 天-空-地-人-业务 PB 级五源采集（§4.5/4.9）。

> 运行时先接**通用 Qwen** 做执行层 Plan，业务语义层用 manifest+OQL+规则约束兜底；训练做后续增强。

### 1.4 建模端（studio-ontology）现状

`map → compile → validate` 三技能是**"LLM-as-compiler"的 prompt+spec，无确定性编译器、无代码无测试**。产出是插件骨架（`__init__.py` + `mappings/objects.yaml` + `cq/golden.yaml`），function-rule 体 / Action 回写 / seed 数据留 `TODO(FDE)` 手工补。→ **它能加速起骨架，但内容 finishing 全靠人工，排期须老实计入。**

---

## 2. 架构订正（落地前必须先钉正的两处）

### 2.1 Graph-RAG 是方案叙述的误设计——防幻觉主机制是 OAG，不是检索

方案 Ch5 §5.9 与 §4.12.6 用同一个"Graph-RAG"罩住了两件本质不同的事：

- **(A) "先约束求解出可行解空间，LLM 在合规候选集内生成"（§4.12.6）= OAG**，非检索。防幻觉来自本体对动作空间的**确定性约束**（越权被拒绝，不是"更不容易"）。
- **(B) "图谱定位 + 向量召回文档片段"（§5.9）= 真正的 RAG**，服务开放问答（`advise` 分支），是软 grounding，保留概率性幻觉。

**订正原则**：
1. 决策/动作路径（出方案 / 评级 / 核算）= **OAG**，走 OQL 查询 + function-backed 规则 + Action guard，确定性、不检索。别叫 Graph-RAG。
2. 知识检索（RAG，可选图谱预过滤）= **仅服务 `advise` 开放问答**，检索标准/专利/案例原文做释义与出处，**结果一律不得直接驱动写入**，必须挂 `source`。
3. 引擎架构本就正确（`advise` 与 `action`/`query` 本就分离），**要改的是方案 Ch5 的叙述**。

> 评审话术："防幻觉不在检索层（RAG 战场），在执行层（OAG）。图谱+向量只用于开放问答取证，从不为需要合规的决策背书。"

### 2.2 遥测读：从"监控域"泛化为"对象绑定的外部读"超集

现状 `telemetry.build_plan` 照**监控**建模（PromQL/ES，per-object series，只产计划不执行）。企业级问草要"从对象读物理承载"的大多是**业务/分析数据**（遥感盖度时序、IoT 墒情、行情流水、逐年成效、监测聚合），落点是 ClickHouse/PostGIS/湖仓。

**做法：泛化成超集，不推倒重来**——保留内核契约（对象绑定 / 声明式 binding / 只产计划不执行 / id 已代入 / 方言白名单 / provider 无关），拆两个 profile：

| Profile | 域 | 方言 | 模式 | 用例 |
|---|---|---|---|---|
| **A · 观测遥测**（现状≈此） | 系统/设备可观测 | PromQL/ES/Loki | 高基数、低延迟 | 装备回执、告警、IoT 健康 |
| **B · 分析读/语义指标**（新增数仓面） | 业务与派生量 | ClickHouse/Trino/PostGIS SQL | 维度化、聚合 | 退化趋势、行情走势、逐年成效、载畜量聚合、碳汇时序 |

要点：
- **binding 升级**：`SeriesSpec`（单序列）→ 能表达 维度/度量/聚合/时间粒度/过滤 的**语义指标定义**（headless-BI 风格）。Function（派生量）可 backed by 数仓查询计划。这就是 §4.12.3 的"虚拟(OBDA)"——一个自研轻量 OBDA。
- **按"是否 gate 写入"分流**：rule-critical 派生量（载畜量喂 Action guard）→ **物化**，引擎直读；analytical 派生量（监管看趋势）→ **虚拟 plan-only**，递回数仓跑。放开"telemetry 永远 plan-only"。
- **选型**：首选扩展现有 plan-generator 直接产 ClickHouse/PostGIS SQL（复用已证明的安全契约），Ontop 留作复杂明细联邦的可选兜底。计费从算子级 → 扫描量/分区/物化命中。
- **排期**：Profile B 主要服务监管趋势/行情/碳汇，是 Phase 1.5/2 用例。**现在只钉抽象与边界，实现等用例落地**，7 月不做满。

---

## 3. 分阶段落地计划

FDE 原则：不 boil the ocean。不铺全量 25 实体，从两条能产生真实业务价值的闭环倒推最小对象集。

### Phase 0 · 冷启（2026.06，2–3 周）——起点是 grass 插件，不是零

| 项 | 内容 |
|---|---|
| 目标 | 锁定 `草修·一地一方` + `草易·快检评级` 两条闭环，跑通"真实数据→约束→动作→审计" |
| 对象集 | 见 §4，最小 ~8–10 类（子图 1/2/3），**不做全量 25 类** |
| 建模 | studio-ontology `map→compile` 起骨架 → FDE 手填 function-rule 体 / Action 回写 / seed |
| 数据 | 蒙草乡土名录 + 若干修复案例 + 快检样本，经 `tenant/ingest` 落库（`tenants/mengcao` sample 为模板） |
| 架构订正 | 落地 §2.1 叙述订正；钉 §2.2 遥测抽象边界（暂不实现 Profile B） |
| 交付物 | 两条闭环可演示（含 Explorer "过程可溯" 界面）；CQ 套件；本体可行性评审附录 |
| 验收 | 两条闭环各自的 CQ 黄金问题通过；乡土合规拦截、越权 reject、HIL 路由可复现 |

### Phase 1 · 首发 MVP（2026.07 绿色算力大会）

| 项 | 内容 |
|---|---|
| Schema | 6 大子图**在 schema 层打通**（对象+关系齐） |
| 上线 | 仅 **2 个 Action 闭环**走真实流程（对齐 §4.12.10 一期） |
| 新增 | 知识检索（RAG）MVP 服务 `advise`（Milvus/pgvector）；real-Qwen 抽检固化为回归 |
| 数据集 | 高质量数据集 v1（清洗+标注+确权登记先行先试） |
| 交付物 | 首发标杆 MVP + 五智能体中 2 个最小可用 + 数据集 v1 |
| 验收 | 黄金问题集分批通过；首发演示脚本可复跑 |

### Phase 1.5 · 数仓面接入（2026.08–10，用例牵引）

监管退化趋势 / 草易行情 / 草碳生物量时序落地时，实现遥测读 Profile B（ClickHouse/PostGIS 方言 + 语义指标 binding + 物化/虚拟分流）。

### Phase 2 · 数据集验收（2026.12）

| 项 | 内容 |
|---|---|
| 规模化 | 全量物化 + NebulaGraph 生产适配 + 真集群压测至千万级三元组 |
| 导出 | 三范式训练集导出器；OKF 读层扩展 |
| 治理 | 本体版本治理上线；tenant schema YAML 化 |
| 验收 | 数据产品登记；本体版本/回放/影响分析闭环 |

### 并行轨（解耦，不阻塞本体交付）

- **训练轨**：问草本体大模型 CPT/SFT/RLHF 独立立项，2027.07 备案版再谈权重内化；此前运行时接通用 Qwen。
- **ML 轨**：22 个模型矩阵按智能体独立排期，以 Action/Function 接入本体。
- **数据工程轨**：五源采集管道独立建设，产出经 `tenant/ingest` 或数仓喂本体。

---

## 4. Phase 0 最小对象/规则清单（两条闭环）

### 闭环 A · 草修·出一地一方

- **对象**：`Site` `SiteType` `Degradation` `RestorationMethod` `SeedPack` `GrassSpecies` `Material` `Region`（可选 `Project` 供成效参考）
- **关系**：`has_site_type` `suffers` `treated_by` `uses` `composed_of` `contains_material` `located_in`（可选 `applied_in`/`achieves`）
- **规则（逻辑层）**：退化分级判定（pre）、乡土合规 草种∈名录（function-backed）、混播 Σ比例=100%、播量∈品种区间、立地适配 `adapts_to`、最佳施工窗口
- **Action（动作层）**：`出一地一方工单`（guard=乡土合规+配比合规；写=方案+工单；HIL=低置信/触硬规则转专家）
- **CQ**："重度盐渍化地块该用哪套种子包配方、能否自动出方案工单并派发？"

### 闭环 B · 草易·快检评级

- **对象**：`Forage` `QualityIndex` `Standard`（可选 `Livestock` `Ration` 供日粮）
- **关系**：`has_quality` `measured_by`（可选 `feeds` `has_ration`）
- **规则**：RFV 分级（function：CP/NDF/ADF→RFV→等级）、霉变阈值拦截
- **Action/Function**：评级定价 + 溯源码（越阈转 HIL）
- **CQ**："这批苜蓿评几级、值不值、依据哪套标准？"

---

## 5. 引擎侧工程补齐清单（🟡，排期）

| 项 | 阶段 | 说明 |
|---|---|---|
| 知识检索 RAG（Milvus/pgvector）服务 advise | P1 | 仅开放问答，不驱动写入 |
| 遥测读 Profile B（数仓方言 + 语义指标 binding + 物化/虚拟分流） | P1.5 | 用例牵引 |
| NebulaGraph 生产适配 + 千万级压测 | P1 起压测 / P2 交付 | 唯一红灯，提前插桩 |
| real-Qwen / real-Nebula 进 CI | P1 | 从手工抽检转回归 |
| OQL 补 OR/排序、`to_ngql` 落地 | P1–2 | 按查询复杂度 |
| tenant schema YAML 化 / plugin.yaml manifest / slots 5、6 | P2 | 声明式化 |
| 三范式训练集导出器 | P2 | 对接数据集验收 |

---

## 6. 风险与缓解

| 风险 | 级别 | 缓解 |
|---|---|---|
| **内容工程人力**（实体/关系/规则抽取需专家+HIL，studio-ontology 只出骨架） | 高 | Phase 0 只做 8–10 对象；领域专家深度投入排期老实计入；HIL 复核前置 |
| **规模化**（InMemory→Nebula 千万级未经真集群验证） | 高 | P1 就起压测，别拖到 P2 |
| **训练绑架交付**（方案耦合叙述） | 中 | 显式切割，运行时接通用 Qwen 先交付 |
| **Graph-RAG 误实现**（向量检索驱动决策） | 中 | 先做 §2.1 叙述订正，堵住方向性错误 |
| **首发过度建设**（为 7 月建满数仓面/全量实体） | 中 | Profile B、5/6 槽位、全量物化一律后置 |

---

## 7. 里程碑时间线

```
2026.06  ── Phase 0 冷启（2–3 周）：两条闭环 + 架构订正 + 评审附录
2026.07  ── Phase 1 首发 MVP：6 子图 schema 打通 + 2 Action 闭环上线 + RAG(advise) + 数据集 v1   ★绿色算力大会
2026.08–10 ─ Phase 1.5：遥测读 Profile B（数仓面，用例牵引）
2026.12  ── Phase 2 数据集验收：全量物化 + Nebula 生产 + 三范式导出 + 版本治理             ★数据集中期验收
2027.07  ── 备案版（并行训练轨交付；本体运行时已稳定运行）                                  ★网信办备案
```

---

## 8. 立即行动项

1. **（半天）** 起草方案 Ch5 的替换叙述（§2.1）：OAG 主机制 / RAG 仅服务 advise。
2. **（半天）** 在本文件基础上补一节遥测读能力重定位设计（§2.2 的接口边界）。
3. **（本周）** 以 `plugins/grass` + `tenants/mengcao` 为基线，落 Phase 0 两条闭环的最小对象/规则清单（§4），跑通 CQ。
4. **（本周）** 拉领域专家确认乡土名录 / 退化分级 / RFV 分级 / 修复案例的数据口径与规则来源（source/citations），落实"来源可查"。
