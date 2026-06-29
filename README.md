# clife-onto-engine · 数智本体基础设施

> 把"数智本体"做成**与行业无关的基础设施内核**，而不是某一个行业大模型的附属层。
> 草业、医疗、金融……各行业大模型的本体层，都以**插件 + 租户配置**的形态跑在同一套内核上。
>
> 一句话：**让 AI 从"会查"升级到"会做且做得对、可追溯"——这是 OAG（行动增强），不是 RAG（检索增强）。**

---

## 目录

- [1. 它解决什么问题](#1-它解决什么问题)
- [2. 核心思想：本体即基础设施 + OAG](#2-核心思想本体即基础设施--oag)
- [3. 五条设计红线](#3-五条设计红线)
- [4. 三层架构：Kernel / Plugin / Tenant](#4-三层架构kernel--plugin--tenant)
- [5. 元模型五要素（内核↔插件唯一契约）](#5-元模型五要素内核插件唯一契约)
- [6. 端到端能力回路](#6-端到端能力回路)
- [7. 内核模块逐一详解](#7-内核模块逐一详解)
- [8. 关键机制深入](#8-关键机制深入)
- [9. Plugin SPI：一个行业怎么接入（7 槽位）](#9-plugin-spi一个行业怎么接入7-槽位)
- [10. 两个示例插件：换行业零改内核](#10-两个示例插件换行业零改内核)
- [11. 完整仓库结构](#11-完整仓库结构)
- [12. 快速开始](#12-快速开始)
- [13. 技术栈](#13-技术栈)
- [14. 安全与合规](#14-安全与合规)
- [15. 设计文档](#15-设计文档)
- [16. 状态与路线图](#16-状态与路线图)

---

## 1. 它解决什么问题

企业数字化做完后常陷入一个困境：**有数据，但缺法则**。系统知道有订单、有地块、有草样，却不知道"谁依赖谁、谁触发谁、谁约束谁"。这缺失的一层就是**本体（Ontology）**。

而 LLM 是概率机器，给不了确定性。当你让 Agent 不只是"回答问题"，而是"执行操作"（出方案、评级、签发凭证、派工单）时，必须有一层**确定性边界**在模型之外把关——

> **大模型负责理解，本体负责确立边界与错误拦截。**

`clife-onto-engine` 就是这层边界的工程实现：一个坐在写路径上、对每一次业务动作做**前置校验 → 内存变更 → 全局规则校验 → 提交或确定性回滚 → 决策血统**的运行时内核。

---

## 2. 核心思想：本体即基础设施 + OAG

### 2.1 本体即基础设施

本体不是某个行业大模型的"知识图谱配件"，而是一套**跨行业复用的运行时内核**。问草（草业）只是它的第一个应用（tenant-zero）；医疗、金融照样能跑在同一内核上。这对应方法论的"AI 原生 OS 内核"——**内核只懂本体怎么运转，不懂任何行业**。

### 2.2 本质是 OAG，不是 (Graph-)RAG

本体语义层的本质是 **OAG（Ontology-Augmented Generation，行动增强，Palantir AIP 提出）**，不是 RAG/Graph-RAG（只读检索增强）：

| 维度 | RAG | OAG |
|---|---|---|
| 增强的对象 | 生成内容的依据 | **行动的能力与边界** |
| LLM 输入 | 检索到的文档片段 | 业务对象 + 可用操作 |
| LLM 输出 | 自然语言答案 | **结构化操作调用** |
| 对世界的影响 | 只读 | **写操作（受规则约束）** |
| 出错后果 | 答案不准 | 状态被错误改变 |
| 追溯性 | 难以还原决策依据 | **完整决策血统** |

GraphRAG / 知识图谱增强检索**仍属"读"**——帮模型理解实体关系，但不提供受治理的写回路径，**挡不住"写错"**。本仓库的核心三件套正是 OAG 的三层能力：

- **操作发现** = 能力清单（`intent/manifest.py`，Schema→能力清单）
- **执行约束** = Action 引擎（guard→写后规则→确定性回滚，`kernel/action_engine.py`）
- **决策追溯** = 审计快照（`trust/audit.py`，存快照非日志）

图库（NebulaGraph）+ OQL 是**本体对象/关系/规则的存储与查询基底**，服务于 OAG 的执行约束（function-backed 规则在写时查图谱）与受治理只读查询——**不是**"检索切片塞进 prompt 再生成"的防幻觉管线。**防幻觉发生在执行层（LLM 提议、引擎回滚），不在检索层。**

> 详见 [`docs/02-oag-positioning.md`](docs/02-oag-positioning.md)（含 OAG vs RAG、OAG vs Skill/MCP 的纠偏卡）。

---

## 3. 五条设计红线

1. **行业概念不进内核** —— `clife_onto_engine/` 源码与测试中禁止出现任何行业词汇（草/种质/碳汇/辣椒…），由 `scripts/check_kernel_purity.py` CI 强制。判缝准则："换成医疗大模型，这段还成立吗？"成立→内核，不成立→插件。
2. **本体是 enforced kernel，不是 advisory schema** —— Rule 是"违反就拦截 + 回滚"，不是"希望遵守"。
3. **受治理的写** —— 所有业务动作经 Action 引擎：guard→变更→写后校验→提交/回滚→审计，无旁路。
4. **开源优先、薄适配** —— 能用成熟开源就用（NebulaGraph/PyYAML/openai SDK/OKF 可视化器），自研只做"接缝"（五要素契约、SPI、Action 流水线）与薄适配。
5. **多租户硬隔离** —— 一个 `ontology_id` ↔ 一个 NebulaGraph space + Capability 租户作用域 + 记忆按 session/ontology 隔离。

---

## 4. 三层架构：Kernel / Plugin / Tenant

对应方法论"三层训练工程经济学"——机制、策略、实例三层分离：

| 层 | 目录 | 归属 | 含行业词汇 | 内容 |
|---|---|---|---|---|
| **Kernel** 内核（机制） | `clife_onto_engine/` | clife，一次性投入、跨行业复用 | **否**（CI 强制） | 元模型、Action 内核、规则引擎、回滚、审计、置信度、记忆、编排、查询、意图编译、OKF 导出 |
| **Plugin** 行业插件（策略） | `plugins/<industry>/` | clife + 行业专家，每行业一份 | 是（隔离在插件内） | 五要素 Schema、映射、规则函数、Action handlers、Agent、CQ |
| **Tenant** 租户配置 | `tenants/<customer>/` | 客户，每客户一份 | 是（实例数据） | 私有物理映射、实例数据接入、密级与授权 |

> 内核与插件**只通过 `clife_onto_engine/sdk/`（Plugin SPI）通信**——目录边界即红线。
> 注：发行/包名 `clife-onto-engine`，可导入的 Python 包名 `clife_onto_engine`（PEP 8）。

---

## 5. 元模型五要素（内核↔插件唯一契约）

内核只理解五种元类型。任何行业概念都是插件用它们声明出来的实例。

| 元类型 | 角色 | 判定标准 | 草业实例（来自插件） |
|---|---|---|---|
| **Object** | 业务实体 | 有独立生命周期 / 属性集 / 被引用 | `Site`、`GrassSpecies`、`Germplasm` |
| **Link** | 有向关系 | 连接两 Object，可带属性、带边语义 | `suffers`、`treated_by`、`uses` |
| **Function** | 只读派生量 | 汇聚多对象计算，无副作用 | `载畜量`、`RFV分级` |
| **Rule** | 全局不变式 | 任何入口写入都强制校验，违反则回滚 | `乡土合规`、`霉变拦截` |
| **Action** | 受审计的业务动作 | 有名、有前置、有副作用、需留痕 | `出一地一方`、`快检评级` |

```python
# 插件用 SPI 声明（grass）——内核只解析结构，不理解语义
@spi.action("grass", "出一地一方",
    params=(ParamSpec("site_id", "ref(Site)", required=True),
            ParamSpec("species", "list", required=True),
            ParamSpec("budget", "number")),
    guards=("预算非负", "角色权限"),       # 前置 declarative 校验
    post_rules=("乡土合规",),             # 写后强制校验（违反即回滚）
    writes=("Project", "SeedPack"))
def emit_restoration_plan(ctx):           # ctx 是受限 Capability，非裸 context
    ctx.stage_write("SeedPack", f"sp_{ctx.params['site_id']}", {...})
    ctx.set_confidence(0.82)
    ctx.add_evidence(source="DB15/T-退化分级标准")
```

> 完整规范见 [`docs/01-metamodel-and-plugin-spi.md`](docs/01-metamodel-and-plugin-spi.md)。

---

## 6. 端到端能力回路

```
          一句口语 / 表单 / 经纬度
                │
                ▼
   ┌──────────────────────────────┐
   │ 意图编译器 (intent/)          │  OAG 操作发现：能力清单约束 LLM 在已声明动作内提议
   │  NL → 结构化意图 + 内核校验    │  越界动作/参数→拒；缺参→澄清；低置信→澄清/HIL
   └──────────────┬───────────────┘
                  │ 写入 CONTEXT 记忆
                  ▼
   ┌──────────────────────────────┐
   │ 多智能体编排 (orchestration/) │  共享记忆 IPC + Router 最小权限 + DAG
   │  intent → act（不传消息，读写分层记忆）
   └──────────────┬───────────────┘
                  │
                  ▼
   ┌──────────────────────────────┐
   │ Action 引擎 (kernel/)         │  guard → 内存变更(live index) → 写后规则(查图谱)
   │  → 提交/确定性回滚 → 审计快照  │  LLM 提议、本体兜底：合法动作违反规则照样回滚
   └──────────────┬───────────────┘
                  │
                  ▼
        GraphStore SPI → NebulaGraph / 内存后端
                  │
                  ▼
   导出 OKF v0.1 知识包 + 离线交互式知识图谱（治理审计/演示）

   贯穿：四层记忆(memory/) · 置信度总线/审计(trust/) · Capability 沙箱(sdk/)
```

---

## 7. 内核模块逐一详解

`clife_onto_engine/`（每个模块都与行业无关、可独立交付）：

| 模块 | 职责 | 关键类型/接口 |
|---|---|---|
| `metamodel.py` | 元模型五要素的 dataclass 契约 | `ObjectType` `LinkType` `FunctionDef` `RuleDef` `ActionDef` `ParamSpec` `HilPolicy` `Severity/Backing/Evaluation/EdgeSemantics` |
| `sdk/` | **Plugin SPI**：插件唯一入口 | `spi.function/rule/action` 装饰器、`Registry`、`Capability`（受限句柄）、`MappingRegistry`、`RuleResult`、`errors` |
| `kernel/` | **Action 执行内核（心脏）** | `ActionEngine`（guard→变更→写后校验→提交/回滚）、`StructuredRejection` `ActionResult` `ActionPreview` `Violation` |
| `query/` | **GraphStore SPI + 查询** | `GraphStore` Protocol、`InMemoryGraphStore`、`QueryView`(overlay 写即可见)、`search_around`、`oql.py`(受限查询)、`nebula_store.py`(adapter) |
| `memory/` | **四层记忆内核** | `Layer`(CRITICAL/RULE/CONTEXT/BACKGROUND)、`MemoryStore`、`classify`(三维分类)、`assemble`(token 预算装配) |
| `trust/` | **信任基础设施** | `AuditStore`/`AuditSnapshot`(存快照)、`ConfidenceBus`(置信度路由→HIL) |
| `orchestration/` | **多智能体编排** | `AgentSpec` `AgentContext` `SharedMemory`(IPC) `Orchestrator`(DAG+环检测+Router 最小权限) |
| `intent/` | **意图编译器（接 LLM）** | `IntentCompiler`、`OpenAICompatibleClient`(provider 无关)、`build_manifest`(能力清单)、`make_intent_agent/make_action_agent` |
| `okf.py` | **OKF 导出** | `export_bundle`(registry → OKF v0.1 知识包) |

---

## 8. 关键机制深入

### 8.1 Action 流水线的三条铁律

```
guard(declarative) → 内存变更(handler 暂存进 live index，写即可见)
  → 写后规则校验(declarative + function-backed 查图谱，收集全部不短路)
  → 全部通过：异步 flush + 审计快照 + HIL 路由 + 副作用编排
  → 任一 hard 违反：确定性回滚 + 结构化拒绝
```

1. **规则在写入"后"执行** —— 全局不变式（载畜量、Σ配比=100%）须看到新状态。
2. **多规则违反时收集全部、不短路** —— 让 Agent 一次看到所有问题再改。
3. **拒绝是结构化数据，不是异常** —— 返回 `{violated_rules, state_snapshot, suggestions}`，供 Agent 自动重试。

**commit 原子性（非事务后端 all-or-nothing）**：提交期逐个写入并记 before-image（undo-log），
任一写失败即反向补偿回滚到提交前；commit 失败以 `StructuredRejection(phase="commit")` 返回。
外加 commit journal（WAL 雏形）记 `pending→committed/compensated`，为崩溃恢复留入口。

### 8.2 Capability 沙箱（受限能力四层约束）

插件代码只拿到 `Capability` 门面（不是裸 context），进程内做四层真校验：

1. **租户/类型作用域** —— 只能访问本 `ontology_id` 内已声明的对象/关系；跨租户结构上不可能。
2. **写声明强制** —— `stage_write` 只允许当前 Action `writes` 里声明过的类型。
3. **Function 最小权限** —— `call_function` 期间读取被限制在该 Function 的 `reads` 集内。
4. **能力收窄** —— 内核内部（view/changeset/base store）名称改写私有，门面不暴露。

外加 `scripts/check_plugin_capabilities.py` 静态 CI 兜底进程内挡不住的逃逸（网络/子进程/动态执行/内核直达）。

### 8.3 OQL 受限查询

LLM **不写 Cypher/nGQL**，只生成**结构化 OQL AST**（JSON 形，天然防注入），运行时校验（引用未声明对象/关系/算子即拒）+ 翻译执行。`Search Around` 算子替代 JOIN 做多跳；产出**算子级成本计量**（base/search-around/aggregation），兼作 SaaS 计费依据。同一个 OQL 既在内存后端跑，也编译成 nGQL 在 NebulaGraph 跑。

### 8.4 四层记忆（类比 CPU 多级缓存）

| 层 | 类比 | 特性 | token 预算 |
|---|---|---|---|
| CRITICAL | L1 | 硬约束，永不驱逐、**全量注入不过滤** | 200 |
| RULE | L2 | 任务相关规则，按相关性动态加载 | 500 |
| CONTEXT | L3 | 近期对话，滑动窗口 | 400 |
| BACKGROUND | MainMem | 背景知识，按需换入 | 300 |

三维分类（动词/来源/绑定实体）+ 淘汰（置信度衰减、规则变更级联作废、生命周期降温）+ token 预算装配（CRITICAL 置顶永驻，其余超预算压缩/丢弃低优先项）。

### 8.5 意图编译器：LLM 提议、本体兜底

NL → 能力清单约束下 LLM 选操作填参 → 内核确定性校验（动作存在、参数名⊆声明、必填齐全）→ 越界拒/缺参澄清/低置信澄清。**关键证明**：LLM 可以生成一个语法合法、置信 0.95 的动作（用非乡土草种修复），本体引擎照样确定性回滚——防线在模型之外。

### 8.6 OKF 导出 + 离线可视化

把规则的**出处/引用**（`RuleDef.source/citations`）+ 全本体导成 **OKF v0.1**（Google 开放知识格式）知识包：每个对象/关系/规则/动作一个 `.md` 概念，规则带 `# Citations`，无引用的规则自动标注"待补"（治理缺口审计）。再用 vendored 的 OKF 官方可视化器渲染成**完全离线、单文件、按类型上色 + 图例**的交互式知识图谱（`viz.html`）。

> OKF 是规则的**文档/出处/版本层（读）**，不替代规则执行（引擎）。详见 [`docs/03-okf-positioning.md`](docs/03-okf-positioning.md)。

---

## 9. Plugin SPI：一个行业怎么接入（7 槽位）

一个新行业 = 一个插件包 + **不改一行内核代码**：

| # | 槽位 | 形态 |
|---|---|---|
| 1 | Schema 包 | 五要素声明（`spi.add_object` / `spi.rule` / `spi.action` …） |
| 2 | 映射注册表 | 声明式 YAML：对象→物理表/列、物化策略（虚拟/物化/混合）、MDO 多源 |
| 3 | Function/Rule 实现 | 经 SPI 注册的函数体（唯一写"代码"处，沙箱回调） |
| 4 | Action handlers | 副作用编排 |
| 5 | 记忆词典 + 提示词骨架 | Schema 驱动 |
| 6 | Agent 角色定义 | runtime 专家 + 权限矩阵 + HIL 关口（或复用通用 intent/act agent） |
| 7 | CQ 验收集 | 本体能力验证问题 |

---

## 10. 两个示例插件：换行业零改内核

| | `plugins/grass`（问草·草业） | `plugins/chili`（辣椒） |
|---|---|---|
| Action 1 | 出一地一方（生态修复出方案） | 制定种植方案 |
| Action 2 | 快检评级（饲草品质） | 辣椒分级 |
| function-backed 规则 | 乡土合规 | 品种适配 |
| 派生量 Function | RFV分级 | 等级计算 |
| 阈值拦截 | 霉变拦截 | 残次拦截 |

两个插件用**完全相同**的内核机制，在**同一个 registry** 中按 namespace 隔离共存（双本体联邦最小形态）。导出的两张知识图谱并排看，是**同构的 OAG 骨架**（对象↔规则↔动作），只换了领域词——这就是"换行业零改内核"的可视化证据。

---

## 11. 完整仓库结构

```
clife_onto_engine/              # 内核（与行业无关，CI 强制纯净）
  metamodel.py                  # 元模型五要素 + ParamSpec/HilPolicy
  sdk/                          # Plugin SPI
    __init__.py                 #   公开面（插件唯一 import 入口）
    registry.py                 #   spi.function/rule/action 注册 + Registry
    capability.py               #   Capability 受限句柄（沙箱四层约束）
    context.py                  #   ActionContext（内核内部运行态）
    mapping.py                  #   映射注册表（槽位 2）
    errors.py                   #   异常
  kernel/
    action_engine.py            #   Action 流水线（心脏）
    rejection.py                #   结构化拒绝 / 裁决结果
  query/
    __init__.py                 #   GraphStore SPI + InMemory 后端 + QueryView
    oql.py                      #   OQL 受限查询 + 成本计量 + 编译 nGQL
    nebula_store.py             #   NebulaGraph adapter（薄）
  memory/                       # 四层记忆（item/store/classify/retrieval）
  trust/                        # 审计快照 + 置信度总线
  orchestration/                # 多智能体编排（共享记忆 IPC/Router/DAG）
  intent/                       # 意图编译器（manifest/llm/compiler/agents）
  okf.py                        # OKF 导出器
plugins/
  grass/                        # 问草·草业（tenant-zero）
  chili/                        # 辣椒（第二行业，证明零改内核）
tenants/
  mengcao/                      # 蒙草租户配置（占位）
docs/
  01-metamodel-and-plugin-spi.md  # 宪法：元模型五要素 + Plugin SPI 规范
  02-oag-positioning.md           # OAG vs RAG/Skill 纠偏卡
  03-okf-positioning.md           # OKF 定位（文档层非执行层）
deploy/nebula/                  # 本地 NebulaGraph docker-compose + 说明
third-party/
  okf-visualizer/               # vendored OKF 官方可视化器（Apache-2.0 + PROVENANCE）
scripts/                        # CI 检查 + 各模块 smoke / 集成 / 导出
requirements.txt
```

---

## 12. 快速开始

### 安装

```bash
pip install -r requirements.txt        # openai + PyYAML（nebula3-python 可选）
```

### 离线即可跑（无需 docker / LLM）

```bash
python scripts/check_kernel_purity.py        # 内核防腐检查（内核无行业词汇）
python scripts/check_plugin_capabilities.py  # 插件静态能力检查（无逃逸/内核直达）
python -m plugins.grass.demo                 # Action 闭环：commit / 回滚拒绝 / validate 预演
python scripts/smoke_graphstore.py           # GraphStore SPI + Search Around + 映射注册表
python scripts/smoke_oql.py                  # OQL 多跳 / 成本计量 / 防注入 / 编译 nGQL
python scripts/smoke_sandbox.py              # SPI 沙箱：四层能力约束都拦得住
python scripts/smoke_memory.py               # 记忆四层：分类 / token 预算 / 淘汰
python scripts/smoke_orchestration.py        # 多智能体：共享记忆 IPC / Router / DAG → Action
python scripts/smoke_atomic.py                # commit 原子性：后端中途失败 → undo-log 补偿全回滚
python scripts/smoke_persistence.py           # SQLite 审计/journal 持久化 + 崩溃恢复回滚孤儿提交
python scripts/smoke_chili.py                 # 第二行业插件（辣椒）：换行业零改内核
python scripts/export_okf.py                  # 本体 → OKF v0.1 知识包 + 离线知识图谱 viz.html
```

### 接 LLM（意图编译器，需 Qwen/OpenAI 兼容端点）

在仓库根放 `llm.local.json`（已 gitignore，绝不入库）：

```json
{ "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "model": "qwen3.5-plus",
  "api_key": "sk-..." }
```

**统一门面 CLI（一句口语进，做/查/澄清出）—— 推荐从这里体验：**

```bash
python scripts/repl.py grass        # 交互式：敲中文问/做事
# 或管道：
echo "巴彦淖尔有哪些地块？" | python scripts/repl.py grass
```

```
== 数智本体会话 · 本体=grass · 角色=施工方 · 模型=qwen3.5-plus ==
> 巴彦淖尔有哪些地块？
  [查询] 1 行 · [{'parcel_id': 'parcel_001', 'region': '巴彦淖尔', 'site_type': '盐碱'}]
> parcel_001 能用哪些修复方法？
  [查询] 2 行 · [{'name': '喷播'}, {'name': '补播'}]      # LLM 自建多跳 OQL
> 给 parcel_001 出一地一方，用碱茅披碱草，预算300
  [已执行] 写入 [('SeedPack','sp_parcel_001'), ('Project','proj_parcel_001')]
> 给 parcel_001 出方案，用紫花苜蓿，预算300
  [被拒] 违反 ['乡土合规']     # LLM 提议合法动作，本体引擎确定性回滚
```

底层是 `clife_onto_engine.Session` 门面：一次 `ask(口语)` 跑完整回路（记忆接地 → 意图编译路由
→ 查 OQL / 做 Action（guard/写后规则/回滚/审计）→ 回写记忆）。

**单环节 smoke：**

```bash
python scripts/smoke_session.py              # Session 门面：做/查/澄清/回滚从一个入口路由
python scripts/smoke_intent.py               # NL → 校验后 Action → 真引擎 commit
python scripts/smoke_product.py              # 端到端产品回路：口语 → 多智能体 → commit（含澄清/回滚）
python scripts/smoke_query.py                # 意图编译器查路径：NL → 结构化 OQL → schema 校验 → 执行
```

### 真实图库（NebulaGraph，需 docker）

```bash
docker compose -f deploy/nebula/docker-compose.yml up -d
pip install nebula3-python
python scripts/nebula_integration.py         # GraphStore SPI + OQL 跑在真实 NebulaGraph
python scripts/nebula_action.py              # Action 闭环（commit/回滚）跑在真实 NebulaGraph
python scripts/nebula_pushdown.py            # OQL 谓词下推：region 落原生列+索引，库内 WHERE 过滤
```

> NebulaGraph 部署细节见 [`deploy/nebula/README.md`](deploy/nebula/README.md)。

---

## 13. 技术栈

- **语言**：Python 3.10+（零强制外部依赖即可跑内存后端 + 离线检查）
- **图库**：NebulaGraph 3.8（一 ontology 一 space，多租户硬隔离）；OBDA 虚拟兜底规划用 Ontop
- **LLM**：任意 OpenAI 兼容端点（默认接阿里 DashScope/Qwen），provider 无关 adapter
- **依赖**：`openai`、`PyYAML`（核心）；`nebula3-python`（真图库可选）
- **知识互操作**：OKF v0.1（Google 开放知识格式）导出 + vendored 官方可视化器
- **开源优先**：自研只做接缝（五要素契约/SPI/Action 流水线）与薄适配

---

## 14. 安全与合规

- **内核防腐 CI**（`check_kernel_purity.py`）：内核出现行业词汇即失败——保证"换行业零改内核"。
- **插件能力 CI**（`check_plugin_capabilities.py`）：插件出现网络/子进程/动态执行/内核内部直达即失败。
- **密钥处理**：LLM 凭据只从 env / gitignore 的 `llm.local.json` 读取，**绝不入源码、不入库**。
- **多租户隔离**：space-per-ontology + Capability 租户作用域 + 记忆 session/ontology 隔离。
- **可追溯**：每次 Action 落审计快照（AI 看到什么、评估哪些规则、为什么这样判），支持回溯。

---

## 15. 设计文档

| 文档 | 内容 |
|---|---|
| [`docs/01-metamodel-and-plugin-spi.md`](docs/01-metamodel-and-plugin-spi.md) | **宪法**：元模型五要素 + Plugin SPI 规范、Action 生命周期、双层校验、审计快照、命名空间隔离 |
| [`docs/02-oag-positioning.md`](docs/02-oag-positioning.md) | OAG vs RAG/Graph-RAG、OAG vs Skill/MCP 的层次纪律 + 纠偏卡 |
| [`docs/03-okf-positioning.md`](docs/03-okf-positioning.md) | OKF 定位：规则的文档/出处/版本层（读），非执行层；与引擎互补 |
| [`deploy/nebula/README.md`](deploy/nebula/README.md) | 本地 NebulaGraph 起停、ADD HOSTS、隔离模型 |

---

## 16. 状态与路线图

### 已完成

- [x] 平台定位 + 三层接缝 + 元模型/SPI 规范
- [x] 元模型五要素 + Plugin SPI + Action 流水线（guard/live-index/双层校验/回滚/审计/HIL）
- [x] 内核防腐 CI + 插件能力 CI
- [x] GraphStore SPI（对象/关系/Search Around/overlay 写即可见）+ 映射注册表（虚拟/物化/混合/MDO）
- [x] OQL 受限查询（结构化 AST/防注入/算子成本计量/多跳/编译 nGQL）
- [x] NebulaGraph adapter + 本地 docker-compose，真图库跑通 GraphStore + OQL + Action 闭环
- [x] SPI 沙箱（Capability 四层约束 + 静态能力 CI）
- [x] 四层记忆（三维分类 + token 预算装配 + 淘汰级联）
- [x] 多智能体编排（共享记忆 IPC + Router 最小权限 + DAG）
- [x] 意图编译器接 LLM（NL → 能力清单约束 + 内核校验 → 真 commit）
- [x] 端到端产品回路（口语 → 多智能体 → commit，LLM 提议本体兜底）
- [x] 第二行业插件（辣椒），证明换行业零改内核、双本体共存
- [x] 规则治理出处化 + OKF v0.1 导出 + 完全离线交互式知识图谱（按类型上色 + 图例）
- [x] commit 原子性：undo-log 补偿（后端中途失败 all-or-nothing 回滚）+ commit journal（WAL 雏形）；真 NebulaGraph 验证
- [x] 审计/journal 持久层（SQLite，stdlib 零依赖，同接口可注入）+ 崩溃恢复 `roll_back_pending`（重启回滚孤儿 pending 提交）

### 路线图

- [x] OQL 谓词下推：映射驱动原生列（ASCII 字段落 TAG 列+索引）+ `find_where` 编译 nGQL `LOOKUP WHERE`，库内过滤；非下推谓词引擎再校验（正确性不依赖下推完整度）；真 NebulaGraph 验证（全扫 3 行→下推 2 行）
- [x] 意图编译器 OQL 查路径：NL → 结构化 OQL（多跳/聚合）→ schema 校验（防注入）→ 执行；与"做(action)"路径自动路由（"会查 + 会做"，查路径是 OAG 基底上的结构化受控读、非 RAG）
- [x] **统一应用门面 `Session` + CLI REPL**：一次 `ask(口语)` 收口完整回路（记忆接地→意图路由→查 OQL/做 Action→回写记忆），做/查/澄清/回滚从一个入口出 —— 可演示的产品面（`scripts/repl.py`）
- [ ] 记忆持久层（SqliteMemoryStore，同审计/journal 模式）
- [ ] 数值/非 ASCII 列的下推（当前原生列为 ASCII string；数值比较与中文字段名走引擎再校验）
- [ ] search_around 步谓词下推（当前下推锚点谓词；多跳步过滤仍在引擎侧）
- [ ] 意图编译器接 OQL "查"路径（当前 "做" 路径已通）+ 记忆压缩用真 tokenizer
- [ ] 记忆/审计持久层（当前内存，落地换持久后端同接口）
- [ ] 进程/WASM 强隔离（面向不可信第三方插件）
- [ ] YAML Schema 加载器（当前 Python 声明，YAML 是同构落点）

---

## 许可证

本项目（除 `third-party/` 外）采用 **Apache License 2.0**——见 [`LICENSE`](LICENSE) 与 [`NOTICE`](NOTICE)。
选 Apache-2.0 而非 MIT，是因为它自带**专利授权**条款，对要被企业/多租户采用的基础设施更稳妥。

`third-party/okf-visualizer/` 为 vendored 第三方（Google，Apache-2.0；内联的 cytoscape/marked 为 MIT），
**单独授权**，见其 `LICENSE.md` 与 `PROVENANCE.md`。

---

> 本仓库为"数智本体引擎"的工程实现与验证骨架。
