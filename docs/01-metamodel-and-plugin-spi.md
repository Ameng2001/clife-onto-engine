# clife-onto-engine · 本体内核元模型与 Plugin SPI 规范（v0.1 草案）

> 本文是 `clife-onto-engine`（数智本体基础设施内核）的**宪法**。
> 它定义内核与所有行业本体之间唯一的契约——**元模型五要素**，以及行业接入的扩展点——**Plugin SPI**。
>
> 第一性红线：**内核不认识任何具体行业概念。** 内核只认识元模型；`GrassSpecies`、`载畜量`、`乡土合规` 全部是草业插件用元模型声明出来的实例。本规范的任何条款若引入了行业词汇，即为缺陷。
>
> 状态：草案 · 待评审 ｜ 第一个验证插件（tenant-zero）：`plugins/grass`（问草大模型）

---

## 0. 定位与设计红线

`clife-onto-engine` 是一套**与行业无关**的本体运行时内核。任何行业大模型（草业、医疗、金融……）的数智本体层，都以**插件 + 租户配置**的形态跑在它之上。

三层切分（对齐方法论"三层训练工程经济学"）：

| 层 | 归属 | 内容 | 含行业词汇 |
|---|---|---|---|
| **Kernel** 内核 | clife，一次性投入，跨行业复用 | 元模型、Action 内核、规则引擎、回滚、审计快照、置信度总线、记忆、编排 | **否** |
| **Plugin** 行业插件 | clife + 行业专家，每行业一份 | 五要素 Schema、映射、规则函数、Action handlers、Agent 定义、CQ 集 | 是（隔离在插件内） |
| **Tenant** 租户配置 | 客户，每客户一份 | 私有物理映射、实例数据接入、密级与授权 | 是（实例数据） |

**判缝准则**：任何一段逻辑，问一句"换成医疗大模型还成立吗"。成立 → 内核；不成立 → 插件。

**红线的物理体现**：内核 `clife-onto-engine/` 与插件 `plugins/` 只通过 `sdk/`（SPI）通信。内核单元测试中禁止出现任何行业词汇——此为 CI 强制规则（见 §9）。

---

## 1. 元模型五要素（Kernel ↔ Plugin 唯一契约）

内核只理解五种元类型。插件用它们声明一切。

| 元类型 | 角色 | 判定标准 | 草业实例（来自插件，仅作说明） |
|---|---|---|---|
| **Object** | 业务实体 | 有独立生命周期 / 有独立属性集 / 被他者引用 | `Site`、`GrassSpecies`、`Germplasm` |
| **Link** | 有向关系 | 连接两个 Object，可携带属性 | `suffers`、`treated_by`、`composed_of` |
| **Function** | 只读派生量 | 汇聚多对象数据做计算，无副作用 | `载畜量`、`RFV分级`、`年固碳量` |
| **Rule** | 全局不变式 | 无论从哪个入口写入都强制校验，违反则回滚 | `乡土合规`、`Σ配比=100%`、`方法学年限` |
| **Action** | 受审计的业务动作 | 有名字、有前置条件、有副作用、需留痕 | `出一地一方`、`签发碳汇凭证`、`生成溯源码` |

### 1.1 Object 定义（YAML）

```yaml
# 由插件声明；内核只解析结构，不理解语义
object: Site                      # 类型名（插件命名空间内唯一）
namespace: grass                  # = ontology_id，内核据此做隔离
description: 地块/草场
lifecycle:                        # 状态机（可选）；内核据此校验状态流转合法性
  states: [draft, surveyed, treating, accepted, archived]
  initial: draft
identity:
  primary_key: parcel_id          # 业务主键，多源对象按此列向拼合（MDO）
properties:
  - { name: area_mu,    type: number, unit: 亩, required: true }
  - { name: geom,       type: geometry, srid: CGCS2000 }
  - { name: site_type,  type: enum, values: [沙地, 盐碱, 矿山, 边坡, 草原, 光伏迹地] }
  - { name: tenure,     type: string, classification: confidential }  # 字段密级
source_required: true             # 实例须携带 source（来源可查）
```

### 1.2 Link 定义

```yaml
link: treated_by
namespace: grass
from: Degradation                 # 源 Object 类型
to: RestorationMethod             # 目标 Object 类型
cardinality: N:N
edge_semantics: hypothesis        # 内核用于"该停在哪"推理：root_cause | hypothesis | derivation
properties:
  - { name: applicability, type: number }
```

> `edge_semantics` 是内核唯一需要理解的"边的程序语义"：遇到 `root_cause` 边可终止多跳推理，遇到 `hypothesis` 边继续追溯。具体哪些边是 root_cause 由插件标注，内核不预设。

### 1.3 Function 定义（只读派生量）

```yaml
function: 载畜量
namespace: grass
returns: { type: number, unit: 羊单位 }
reads: [MonitorObs, Site]         # 声明读取的对象类型（内核据此做权限/缓存）
impl: grass.functions.carrying_capacity   # 指向插件经 SPI 注册的实现（§4.3）
side_effects: false               # 内核断言：Function 永不写入
```

### 1.4 Rule 定义（全局不变式）

```yaml
rule: 乡土合规
namespace: grass
severity: hard                    # hard=违反即回滚 ｜ soft=advisory 仅告警
evaluation: post_write            # 关键：写入后校验（需看到新状态）。见 §3
scope:                            # 触发条件：哪些 Action / Object 变更会激活本规则
  on_actions: [出一地一方]
backing: function                 # declarative=纯参数校验 ｜ function=需查图谱（重校验）
impl: grass.rules.native_species_compliance
message_template: "草种 {species} 不在 {region} 乡土名录，已拦截"
```

> **双层校验**是内核硬约束：`declarative` 规则只看参数/用户上下文（轻、快）；`function` 规则可读图谱/跨对象（重、准）。内核负责调度两层并在 hard 违反时回滚，校验逻辑本身在插件。

### 1.5 Action 定义（受审计的业务动作）

```yaml
action: 出一地一方
namespace: grass
description: 对一个退化地块生成修复方案并派单
params:
  - { name: site_id,  type: ref(Site), required: true }
  - { name: budget,   type: number, unit: 元/亩 }
guards:                           # 前置校验（declarative，能不能启动）
  - { rule: 面积为正 }
  - { rule: 角色权限, role: [施工方, 牧民, 监管] }
validate_supported: true          # 支持无副作用预演（试算造价/配比）。见 §3.4
writes: [Project, SeedPack]       # 声明写入的对象类型
post_rules: [乡土合规, 配比合规, 安全间隔]   # 写后强制校验的 Rule
side_effects:                     # 通过后的副作用编排（内核同事务调度）
  - { type: workitem, template: 修复施工工单 }
  - { type: webhook,  on: accepted }
hil:                              # HIL 关口：满足条件则强制人工复核
  required_when: "confidence < 0.75 OR severity_touched == hard"
  reviewer_role: 乡土草种合规官
audit: snapshot                   # 内核强制：落快照式审计（见 §5）
```

---

## 2. 命名空间与多本体隔离

- 每个本体有全局唯一 `ontology_id`（= 插件 `namespace`）。
- 内核中**所有**对象/关系/规则/记忆/审计/计量记录都带 `ontology_id` 前缀，物理上可分库分租户。
- **数据平面按租户隔离**：映射注册表（§4.2）指向各租户自己的物理库，跨租户默认零可见。
- **联邦（远期）**：跨域协作通过显式声明的"共享上层本体"做受控引用，不得把两套 schema 揉合。M1 只做隔离，不做联邦。

---

## 3. Action 执行内核生命周期（内核的"心脏"）

内核对每个 Action 执行固定流水线，**与行业无关**：

```
1. guard 前置校验        declarative：参数取值 + 用户上下文 + 角色权限
2. validate 预演（可选）  无副作用试算，返回预估结果，不进第 3 步
3. 内存变更              写入 live index —— 写即可见
4. 写后规则校验          post_rules：declarative + function（查图谱）两层
                         多规则违反 → 收集全部，不短路
5a. 全部通过            异步 flush 持久化 + 同事务落审计快照 + 副作用编排
5b. 任一 hard 违反      确定性回滚 + 返回结构化拒绝（触发规则 / 状态快照 / 建议调整）
```

### 3.1 三条内核铁律（来自方法论，不可妥协）

1. **规则在写入"后"执行**——全局不变式需要看到新状态。
2. **多规则违反时收集全部、不短路**——让调用方/Agent 一次看到所有问题再改。
3. **拒绝是结构化数据，不是异常**——返回 `{violated_rules, state_snapshot, suggestions}`，供 Agent 自动重试。

### 3.2 一致性模型

- **单对象读后写强一致**：写 live index 即可见（草修出方案后立即可查）。
- **列表/聚合最终一致**：大范围扫描容忍秒级延迟（异步 flush）。

### 3.3 双写路径（内核区分两类写入）

| 路径 | 来源 | 是否过 Action 闸门 | 目的 |
|---|---|---|---|
| **数据摄取路径** | 高吞吐遥测（遥感/IoT/CDC） | 否，直接流式物化 | 保吞吐 |
| **治理变更路径** | Action 业务回写（出方案/凭证/补贴） | 是，全校验全审计 | 保信任 |

### 3.4 validate 预演

`validate_supported: true` 的 Action 必须支持无副作用试算（造价/配比/碳汇收益），走流水线 1→2 后即返回，不进第 3 步。

---

## 4. Plugin SPI：行业接入的 7 个槽位

一个新行业 = 一个插件包 + **不改一行内核代码**。插件包向内核声明/注册以下 7 项：

| # | 槽位 | 形态 | 内核如何消费 |
|---|---|---|---|
| 1 | **Schema 包** | 五要素 YAML（§1） | 解析为运行时元模型 |
| 2 | **映射注册表** | 声明式 YAML：对象→物理表/列、关系→连接键、物化策略 | 驱动 OQL 翻译与 CDC 物化 |
| 3 | **Function/Rule 实现** | 经 SPI 注册的函数体（唯一要写"代码"处，沙箱调用） | 写后校验 / 派生量计算时回调 |
| 4 | **Action handlers** | 每个 Action 的副作用编排 | 5a 阶段调度 |
| 5 | **记忆词典 + 提示词骨架** | Schema 驱动的关键词词典、角色模板 | 记忆检索关键词、Agent 提示 |
| 6 | **Agent 角色定义** | runtime 专家清单 + 权限矩阵 + HIL 关口标注 | 编排器加载、Router 鉴权 |
| 7 | **CQ 验收集** | 本体能力验证问题 + 判定标准 | 上线门禁 / 回归测试 |

### 4.1 插件清单（manifest）

```yaml
# plugins/grass/plugin.yaml
plugin: grass
display_name: 问草大模型
ontology_id: grass
version: 0.1.0
engine_compat: ">=0.1.0"          # 兼容的内核版本
provides:
  schema:    ./schema/            # 槽位 1
  mappings:  ./mappings/          # 槽位 2
  functions: grass.functions      # 槽位 3（含 Rule 实现）
  actions:   grass.actions        # 槽位 4
  memory:    ./memory/dict.yaml   # 槽位 5
  agents:    ./agents/            # 槽位 6
  cq:        ./cq/golden.yaml      # 槽位 7
```

### 4.2 映射注册表（槽位 2）

```yaml
object: Site
materialization: hybrid           # virtual | materialized | hybrid
physical:
  primary: { store: postgis, table: geo_parcel, key: parcel_id }
  multi_source:                   # MDO 列向拼合
    - { store: clickhouse, table: rs_growth,  join: parcel_id }   # 遥感长势
    - { store: clickhouse, table: iot_soil,   join: parcel_id }   # IoT 墒情
quality_gate: { completeness_min: 0.95 }   # 6 维质检阈值（插件设）
```

### 4.3 SPI 注册接口（槽位 3，伪代码）

```python
# 内核提供注册点；插件实现并注册，内核以沙箱回调
@spi.function("grass", "载畜量")
def carrying_capacity(ctx) -> float: ...

@spi.rule("grass", "乡土合规", backing="function", severity="hard")
def native_species_compliance(ctx) -> RuleResult: ...

@spi.action_handler("grass", "出一地一方")
def emit_restoration_plan(ctx) -> Effects: ...
```

> 内核对 `ctx` 提供受限能力：只读 OQL 查询、当前变更集、置信度写入；**不暴露**直接写库、跨租户访问、网络（副作用必须经 Effects 声明，由内核编排）。

---

## 5. 信任基础设施：置信度总线 + 审计快照

### 5.1 审计快照（存快照，不存变更）

每次 Action 落一条不可变审计记录：

```json
{
  "ontology_id": "grass",
  "action": "出一地一方",
  "actor": {"role": "施工方", "id": "..."},
  "inputs_snapshot": { "...": "AI 当时看到的输入" },
  "rules_evaluated": [{"rule": "乡土合规", "result": "pass", "backing": "function"}],
  "decision": "committed",
  "confidence": 0.82,
  "evidence": [{"source": "DB33/T 标准号"}, {"case_id": "..."}],
  "schema_version": "grass@0.1.0",
  "ts": "..."
}
```

> 支持回溯查询：「用当时的 schema_version，这个操作合法吗」。落地"过程可溯、结果可验"。

### 5.2 置信度总线

- 跨层（意图编译 → 本体校验 → 记忆）传播 confidence。
- **低置信被拒** → 诊断为意图编译器理解错；**高置信被拒** → 触发记忆/规则审计。
- HIL 路由由 confidence 阈值 + 是否触碰 hard 规则自动决定（§1.5 `hil.required_when`），不靠人肉判断。

---

## 6. 记忆内核四层（多轮 / 多 Agent 必需）

| 层 | 类比 | 特性 | token 预算 |
|---|---|---|---|
| CRITICAL | L1 | 硬约束，永不驱逐，**全量注入不过滤** | 150–200 |
| RULE | L2 | 当前任务相关规则，动态加载 | 300–500 |
| CONTEXT | L3 | 近期对话工作状态，滑动窗口 | 200–400 |
| BACKGROUND | MainMem | 背景知识，按需换入 | 100–300 |

- 分类驱动：动词特征 + 来源类型 + 绑定实体（Rule 对象→RULE/CRITICAL）。词典由插件提供（槽位 5），机制在内核。
- 淘汰：生命周期状态机（hot→warm→cold→archived）+ 置信度衰减 + 规则变更级联 deprecate。

---

## 7. 查询层：受限 OQL + Search Around + 算子成本计量

- **LLM 不写 Cypher/SQL**，只生成受限 OQL，运行时翻译执行（防注入）。
- `Search Around` 关系算子替代 JOIN，沿关系链跳跃。
- **算子级成本计量**：每次查询按 `base / search-around / aggregation / action` 计量——既是多租户计费边界（呼应词元计费），也是可观测性来源。

---

## 8. 版本治理与配置即 PR

- 五要素 Schema 以 YAML 文本存储，走 git PR 工作流：提交 → 审查 → 合并 → 触发记忆级联 → 通知 Agent → **无需重启即用新规则**。
- **快照隔离**：事务开始锁定 schema_version；**回溯查询**：可用历史版本重判旧操作。

---

## 9. 草业作为 tenant-zero 的验证义务 + 内核防腐 CI

`plugins/grass` 是第一个、也是检验内核接缝是否干净的试金石：

- **若草业必须改内核才能跑通 → 接缝划错，立即修内核而非在草业打补丁。**
- **内核防腐 CI**：`clife-onto-engine/` 源码与测试中出现行业词汇（草/种质/碳汇/载畜量…）即 CI 失败。
- M1 验收：草业插件用本规范跑通**两个 Action 闭环**——`出一地一方` 与 `AI 快检评级`——全流程经 guard→validate→写后校验→审计快照，且内核零行业代码。

---

## 待评审决策点

1. 内核技术栈与语言（Python 快但需关注推理延迟 Gap；是否信创约束）。
2. 运行时实例图：Neo4j vs NebulaGraph；规范本体定义是否引入轻量 OWL/SHACL。
3. SPI 沙箱机制（进程内受限 vs 独立进程/WASM）——决定插件隔离强度与多租户安全。
4. `validate` 预演与正式 Action 的代码复用方式（避免两套配比/造价逻辑漂移）。
