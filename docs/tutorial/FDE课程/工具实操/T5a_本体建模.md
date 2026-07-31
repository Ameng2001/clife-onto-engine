# T5a · 本体建模（studio-ontology）

> 目标：把业务分析编译成**受治理的可运行底座**的结构骨架。**90′**（知识注入 25′ + 实操 45′ + checkout 20′）
> 知识注入：**讲 4 栈③（OAG：认知到行动）**
> 工具：`studio-ontology` v0.1.0（建模端）+ `clife-onto-engine`（运行时端，本地 `~/Codes/onto-fundary-plugins/`）
> 主案例：**grass 完整插件** / **chili 最小插件（含反面）**
>
> ⭐ **T5a 与 T5b 是同一个 180′ 重心的上下半场**：**T5a 建结构**（对象/关系/规则/动作怎么立起来），**T5b 设闸与治理**（哪里必须停下来叫人、怎么验证闸没失效）。中间不要断开排课。

---
## 〇、开场第一句：这不是编译器

学员看到 "compile" 会以为有个确定性编译器。**没有。**

> 运行时仓自己的交付文档写得很直白：`map → compile → validate` 三个技能是 **"LLM-as-compiler" 的 prompt + spec，无确定性编译器、无代码、无测试**。产出是**插件骨架**，内容 finishing 全靠人工。

**为什么开场就要说这句**：因为 T5 的全部价值都建立在这个认知上——

> **机器负责把结构立起来，人负责把判断填进去。**
> 康养项目留了 **121 处 `NotImplementedError`**，这不是没做完，是**明确划出"机器到此为止、人从这里接手"的界线**。
> 一个不敢留 NotImplementedError 的 FDE，会让模型把它猜的业务规则写成看起来能跑的代码——**那才是灾难。**

---
## 一、四个命令 + 一处最好的权限教学

| 命令 | 干什么 | 强制人审 |
|---|---|---|
| `/studio-ontology:map {id}` | 业务分析 → 七段 IR（`ontology-map.md`） | 无 |
| `/studio-ontology:compile {id}` | IR → 插件骨架 | 无（**已存在不覆盖，只告警**） |
| `/studio-ontology:validate {id}` | 四段校验（结构/治理/TODO/CQ） | 无（只诊断） |
| **`/studio-ontology:model {id}`** | **map → ⏸ 你审 IR → compile** | **★唯一有强制停点** |

**课堂用 `model`，不要分开跑** —— 因为那个停点是本步最重要的教学时刻。审 IR 时审四项：**对象边界 / edge_semantics / 规则的 severity·backing·出处 / Action 的 writes·HIL**。你可以直接改 md 文件再继续。

### ⭐ 三个技能的 `allowed-tools` 差异（讲透这个，学员就懂"工具的权限就是它的职责"）

| skill | allowed-tools | 说明 |
|---|---|---|
| `ontology-map` | Read, Write, Glob, Grep, **Agent** | **有 Agent** → 能调专家做头脑风暴与复核 |
| `ontology-compile` | Read, Write, Glob, Grep | **无 Agent** → 纯机械翻译，不许自由发挥 |
| `ontology-validate` | Read, Glob, Grep, **Bash** | **无 Write** → **物理上不可能改你的插件**；有 Bash → 能跑引擎 |

> **校验器无权改代码**——这是"纪律靠机制不靠自觉"最干净的一个例子。
> 它只能告诉你哪里不合格，**不能替你把不合格的地方抹平**。

---
## 二、输入：`domain-intake` 12 段契约

模板：`studio-ontology/templates/domain-intake.md.tmpl`（T1 已经填过 60%，这里补完）

| 段 | 谁填 | → 编译成 |
|---|---|---|
| §0 元信息 | FDE | IR 第 0 段 Header |
| §1 业务概述 | 业务方/PM | **唯一不参与编译的实体段**（定调：哪些是"做"、哪些是"查"） |
| §2 角色 Actors | 业务方/领域专家 | 并入 **Action 的 actor** |
| §3 业务对象 | 领域专家/FDE | **Object** |
| §4 关系 | 领域专家/FDE | **Link**（"因果性质"→ edge_semantics） |
| §5 业务动作 | 业务方 + FDE | **Action** |
| §6 派生指标 | 领域专家 | **Function** |
| **§7 业务规则 ★最关键** | 领域专家 + 规则工程师 | **Rule** |
| §8 决策点 | 领域专家 | **也归 Rule** |
| §9 数据来源 | 数据/IT | 映射注册表 |
| §10 能力问题 CQ | 业务方 + FDE | 验收用例 |
| §11 治理要求 | 合规/法务 + FDE | 并入 **Action 的 hil** + 审计 + 密级 |

> ⚠️ README 说"11 段"，模板实际是 **§0–§11 共 12 段**（README 没数 §0）。按 12 段讲。

### §7 的「规则三问」（本步最该背下来的东西）

> ① **违反了要不要拦住并回滚？**（→ severity: hard / soft）
> ② **只看入参能判，还是要去查别的数据？**（→ backing: declarative / function）
> ③ **依据是哪条标准 / 方法学 / 谁的经验？**（→ source；**没依据就写"待补依据"，不许猜**）

### 填写完成度自检（4 条）
- [ ] §3 每个对象有主键；§5 动作写入的对象都在 §3 出现
- [ ] §7 每条规则标了"拦/告警 + 只看入参/要查 + 依据"；无依据的标了 `待补依据`
- [ ] §5 每个改状态的动作都问过"要不要 HIL"
- [ ] §10 至少 **1 查 + 1 做 + 1 该被拦**

---
## 三、七段 IR（`ontology-map.md`）

> ⚠️ 命名陷阱：规范文件标题写的是「**五段式**中间表示」，正文却是 **0 号 Header + 七段**。**"五"指五要素，"七"指七段**，不是笔误。

| 段 | 内容 | 表格列 |
|---|---|---|
| 0 | Header | `ontology_id / bounded_context / target_dir / source_artifacts / iteration` |
| 1 | **Objects** | `name / primary_key / properties / lifecycle / source` |
| 2 | **Links** | `name / from / to / cardinality / edge_semantics / properties` |
| 3 | **Functions** | `name / reads / returns / intent` |
| 4 | **Rules ★** | `name / severity / backing / evaluation / on_actions / intent / source / citations / check`（**9 列**） |
| 5 | **Actions** | `name / params / guards / post_rules / writes / hil / validate`（**7 列**） |
| 6 | Mapping Hints | `object / store / table / key / columns / materialization` |
| 7 | CQ | YAML list：`- q:` + `expect:` |

### 三组关键取值域

**`edge_semantics` 三值**（决定多跳推理停在哪，IR 里最难的一处判断）：

| 值 | 含义 |
|---|---|
| `root_cause` | **命中即终止追溯**——找到根因了，别再往上查 |
| `hypothesis` | 继续查——这条边只是"可能相关" |
| `derivation` | 纯结构派生——不参与因果推理 |

**`source` 三态**（治理教学的关键）：

| 写法 | 审计结果 |
|---|---|
| 具体标准号（如 `GB 38600-2019`） | ✅ 通过 |
| `通用` | ✅ **通过**——自明常识是合法值，审计放行 |
| `TODO(FDE): 补依据` | ⚠️ **被拦**，计入治理缺口 |

> **"通用"这个值的存在很重要**：它让"我知道这是常识、不是我忘了查"能被表达出来。**留白和"承认这里是常识"是两件事。**

**`expect` 三值（CQ）**：`query` / `action(<动作名>)` / `rejected(<规则名>)`

### 段末完整性自检 7 条
① 每个 Object 有 primary_key、被写入的都已声明 ② Link 的 from/to 都已声明、edge_semantics 已判 ③ 每条 Rule 标了 severity+backing+evaluation ④ 每条 Rule 有 source ⑤ Action 的 guards/post_rules/writes 都存在 ⑥ **合规/对外凭证类 Action 都设了 hil** ⑦ CQ 至少覆盖一查一做一拦

---
## 四、declarative vs function：一句话判据

> **判定所需的全部信息，是不是都在 `ctx.params` + `ctx.actor` 里？**
> **是** → `declarative`（可从 `check` 全自动生成代码）
> **否**（要 `ctx.get` / `ctx.find` / `ctx.search_around`）→ `function`（只能生成骨架，你来填）

规则工程师 agent 的原话值得直接念给学员：

> **"never mark a rule `declarative` if it secretly needs to look up a registry/threshold/inventory — that's `function`"**
> —— 偷偷需要查名录/阈值/库存的，不是 declarative。

**偏好倾向**：合规、安全、方法学类的规则，默认往 **`hard` + `post_write` + `function`** 三档靠。因为那才是回滚机制的用武之地。

### ⚠️ declarative 的取反逻辑（教学易错点）

IR 的 `check` 写的是**合法条件**，生成代码时**取反成违反条件**：

```
IR:    check = budget is None or budget >= 0
生成:  if not (budget is None or budget >= 0):
           return RuleResult.fail(...)
       return RuleResult.ok()
```

学员写 `check` 时最容易写反——**记住：写"什么情况下是对的"，不是"什么情况下要拦"。**

---
## 五、编译产物：机器给你到哪一步

`/studio-ontology:compile` 产出 4 个文件：

| 文件 | 内容 |
|---|---|
| `{target_dir}/__init__.py` | 主体：ONTOLOGY 常量 + Object/Link 注册 + Function/Rule/Action handler + seed 桩 |
| `{target_dir}/mappings/objects.yaml` | ← IR §6，对象→物理表/列/物化策略 |
| `{target_dir}/cq/golden.yaml` | ← IR §7 |
| `{target_dir}/plugin.yaml` | 清单 |

### 四类 `NotImplementedError` 的来源

| # | 触发条件 | 生成物 |
|---|---|---|
| 1 | **function-backed 规则** | 装饰器 + docstring + `# TODO(FDE): 查…` + 可用方法提示 + `raise NotImplementedError` |
| 2 | **每一个 Action handler** | stage_write 骨架注释（逐 writes 一行）+ `set_confidence` + `raise NotImplementedError` |
| 3 | **Function 口径不明** | `# TODO(FDE): 实现派生量计算（只读，无副作用）` + raise |
| 4 | `seed_reference_data` | 不 raise，函数体 `pass` + TODO docstring |

> **declarative 规则是唯一被"全自动生成函数体"的** —— 这就是为什么第四问要问"只看入参能不能判"：**答对了，机器就能替你写完。**

### ⚠️ SPI 七槽位的真相（插件文档不准，必须更正）

`compile-rules.md` 说编译产物"正好填满 SPI 的 7 个槽位"。**实测不是。**

| 槽位 | 编译产物覆盖？ |
|---|---|
| 1 Schema 包 | ✅ `__init__.py` |
| 2 映射注册表 | ✅ `mappings/objects.yaml` |
| 3 Function/Rule 实现 | ⚠️ **只出骨架** |
| 4 Action handlers | ⚠️ **只出骨架** |
| 5 记忆词典 / 术语表 | ❌ **完全不生成** |
| 6 Agent 角色 + HIL 关口声明 | ❌ **完全不生成** |
| 7 CQ 验收集 | ⚠️ 产 YAML，但**格式与引擎不匹配**（见第七节） |

**教学价值**：这张表本身就是"**别信文档，去看代码**"的活教材，也是 T5 收尾清单的由来。

---
## 六、两仓分工（讲清楚，否则学员会把数据写进插件）

```
建模仓（astra-studio 工作区）        运行时仓（clife-onto-engine）
studio/changes/{id}/ontology-map.md  →  plugins/{ontology_id}/     ← 本体定义/规则/动作（行业级，租户无关）
                                        tenants/{tenant}/          ← 该租户的实例与参考数据
```

- **`plugins/{ontology_id}/`**，不是 `plugins/{tenant}/` —— grass 与 chili 在**同一进程同一 registry 里按 namespace 共存**（`ObjectType.namespace = ontology_id`）
- **名录数据、实例数据属于 `tenants/`**，不属于插件
- **IR 文件不在运行时仓**，跨仓复制

---
## 七、⚠️ FDE 收尾清单（6 项，机器帮不了的部分）

编译完成 ≠ 可用。**这 6 项必须人做**：

| # | 做什么 | 在哪做 |
|---|---|---|
| 1 | **填 function-backed 规则体** | `plugins/{id}/__init__.py`：`ctx.get()` 取对象 → `ctx.find()` 查名录 → 比对 → `RuleResult.fail(msg, suggestion=)` / `ok()` |
| 2 | **填 Action handler 回写** | `ctx.stage_write()` / `ctx.stage_link()` / `ctx.emit_effect()` / `ctx.set_confidence()` / `ctx.add_evidence()` |
| 3 | **填 seed 参考数据** | `seed_reference_data(store)`；真实落地走 `tenants/{tenant}/` |
| 4 | **把 CQ 翻成 Python** | ⚠️ 引擎**只认 `plugins/{id}/cq.py` 的 `CQ_SUITE` 元组**，全仓**没有任何代码读 `cq/golden.yaml``。`[查]`→`QueryCQ`、`[做]`→`ActionCQ(expect="commit")`、`[该被拦]`→`ActionCQ(expect="reject", expect_rule=...)` |
| 5 | **改 `plugin.yaml` 成引擎格式** | ⚠️ 模板产的是 `ontology_id:` + `provides:{...}`，引擎 `load_manifest()` 读的是 `doc["ontology"]` + `schema/mappings/glossary/agents`，**完全不认 provides**。还要补 **glossary（槽位5）+ agents（槽位6）** 两段 |
| 6 | **补 `Evaluation` 的 import** | ⚠️ `compile-rules.md` 的固定头部**漏了它**，照着生成 `Evaluation.PRE` 会 **NameError**。sdk 确实导出，加上即可 |

> **第 4、5 两项是硬落差**：不做，编译产物根本跑不起来。**这不是学员做错了，是工具链的已知缺口。**
> ⭐ 顺便回收 **B-9（SDK 能力想当然）**：康养项目当初对 `Evaluation` 是否导出存疑、**统一留 docstring 挂账没敢往前推**——今天证明那个判断是对的。**不确定就挂账，别赌。**

### 红线是两层，别只讲一层

| 层 | 手段 | 强度 |
|---|---|---|
| 建模端 | prompt 指令"只 `from clife_onto_engine.sdk import`，不碰内核内部" | **软约束，无机械检查** |
| **运行时端** | CI 两个脚本必跑 | **硬执法** |

- `check_kernel_purity.py` —— **反向执法**：扫内核代码，命中行业词黑名单（草/碳汇/苜蓿/grass/carbon…）即 exit 1。**保证行业概念只能待在 plugins/ 和 tenants/**
- `check_plugin_capabilities.py` —— **正向执法**：拦插件的逃逸（socket/subprocess/eval）和**内核私有直达**（`._stage(` / `_set_confidence` / `._base` 等）

> **这正是 B-8（越域写入冲动）的物理对应**：你在凌晨三点想抄近路直接摸内核私有方法，**CI 会挂给你看**。
> **结构纪律靠校验器，不靠自觉。**

---

---

## 八、💡 启发范例

### 讲"完整插件长什么样" → 看 `plugins/grass/`

四件齐全，且已按闭环拆文件（规模化范例）：
`__init__.py`（schema + guard + 主 Action + seed）· `forage.py`（快检评级）· `carbon.py`（碳汇核算）· `breeding.py`（杂交推荐）· `machinery.py`（作业参数）· **`cq.py`（25 条 CQ_SUITE）** · **`plugin.yaml`（glossary + agents）** · `mappings/objects.yaml`

### 讲"最小可读插件" → 看 `plugins/chili/`

只有 `__init__.py` + `grading.py` + `mappings/`。**没有 plugin.yaml、没有 cq.py。**

> ⚠️ 顺带回收案例矩阵的诚实分层：chili 的本体是 **objects 5 / links 0（连 links 目录都没有）**。
> **只建对象不建关系，本体就退化成一张数据字典**——五要素里 Link 缺位，Function 无处派生、Rule 无处横切。
> **把 grass（3 条 Link）和 chili（0 条）并排看，一眼就明白"五要素为什么缺一不可"。**

### 讲 intake 怎么填 → 用 `examples/domain-intake-chili.md`

唯一一份填满的完整 intake，**§7 规则段是全插件最好的教学素材**：7 条规则天然分成 **2 条 function-backed + 5 条 declarative**，一次讲清分界判据。§10 CQ 段超额达标（2 查 + 1 做 + 2 拦）。

**但要配三处补丁**（照着讲会缺东西）：
1. **§4 关系段太弱** —— 两条边都是"派生"，**教不了 edge_semantics 三值**。讲 `root_cause` / `hypothesis` 要切回规范文档里的草业例（`Site --suffers--> Degradation` = hypothesis）
2. **没有"待补依据"的负样本** —— 7 条规则 source 全齐，**演示不了 T5b 治理审计的拦截**。要用 intake 模板里草业例的"安全播量…待补依据"
3. **没有密级字段** —— 教不了 `密级=confidential → PropertySpec(classification=)`

---

## 九、知识（讲什么）· 讲 4 栈③：本体建模 OAG（25′）

> 并入自《第 4 讲 · FDE 的知识背景栈》栈③。
> **这一栈是全课程的技术分水岭，也是 C-Life 真正的护城河**：别的方法论我们借业界经典，**本体这一栈我们有自己成体系的方法论**——`clife-onto-engine`（数智本体基础设施），对标 Palantir 本体语义 OS。
> **下面讲的不是教科书概念，是我们自己一行行写出来、CI 强制、跨行业复用的东西。**

### 10.1 这个角色原本是谁

**知识工程师 / 本体工程师**——负责把领域知识落成**机器可推理、可执行、可追溯**的本体，**而不是给人看的 ER 图**。

七个知识栈里，栈②（DDD）和栈③（本体 OAG）合起来才是"建模"。**建模只是七分之二**——这句话在 T5 开头就要说清楚，免得学员以为会建模就等于会做 FDE。

### 10.2 核心命题（本节只记这一句）

> **大模型负责理解，本体负责确立边界与错误拦截。**

LLM 是概率机器，给不了确定性。当你让 Agent 不只"回答问题"而是**执行操作**（出方案、评级、签发凭证、派工单）时，必须有一层**确定性边界在模型之外把关**。

`clife-onto-engine` 就是这层边界的工程实现——一个坐在**写路径**上、对每次业务动作做
`前置校验 → 内存变更 → 全局规则校验 → 提交或确定性回滚 → 决策血统` 的运行时内核。

> 这正是第〇节"这不是编译器"的另一面：**机器立结构、人填判断**，而结构一旦立起来，**它是会执法的**。

### 10.3 方法论内核一：OAG（行动增强）≠ RAG（检索增强）

本体语义层的本质是 **OAG（Ontology-Augmented Generation，行动增强，概念由 Palantir AIP 提出）**，不是 RAG / Graph-RAG（只读检索增强）：

| 维度 | RAG | **OAG** |
|---|---|---|
| 增强的对象 | 生成内容的依据 | **行动的能力与边界** |
| LLM 输出 | 自然语言答案 | **结构化操作调用** |
| 对世界的影响 | 只读 | **写操作（受规则约束）** |
| 出错后果 | 答案不准 | **状态被错误改变** |
| 追溯性 | 难还原依据 | **完整决策血统** |

**关键澄清（学员最容易搞混的一点）**：GraphRAG / 知识图谱增强检索**仍属"读"**——帮模型理解关系，但**不提供受治理的写回路径，挡不住"写错"**。

> **防幻觉发生在执行层（LLM 提议、引擎回滚），不在检索层。**
> 一句话记住：**概率推理在"选择层"，确定性约束在"执行层"。**

> ⚠️ **诚实标注（课上必须说）**：给客户讲草业项目时我们曾用"Graph-RAG 约束求解防幻觉"的话术贴近客户认知，但那**把 OAG 的功劳记到了 RAG 头上**——对外可以将就，**对内必须讲准**（见 `docs/02-oag-positioning.md` 纠偏卡）。

### 10.4 方法论内核二：OAG 三件套（缺一不可）

| 件 | 是什么 | 在本课的落点 |
|---|---|---|
| **操作发现** | 能力清单：Schema → 可用 Action + 参数 | 编译产物的 ONTOLOGY 常量与 Action 注册 |
| **执行约束** | Action 引擎 `guard → 写后规则 → 确定性回滚` | 第一节的四命令 + T5b 的写入闸 |
| **决策追溯** | 审计**快照**，不是日志 | `set_confidence` / `add_evidence` / HIL 留痕 |

### 10.5 方法论内核三：五条设计红线

1. **行业概念不进内核**——内核源码禁止出现任何行业词（草 / 碳汇 / 辣椒 / 康养…），CI `check_kernel_purity` 强制。判缝准则：**"换成医疗大模型这段还成立吗？"** 成立 → 内核，不成立 → 插件。
2. **本体是 enforced kernel，不是 advisory schema**——Rule 是"违反就拦截 + 回滚"，不是"希望遵守"。
3. **受治理的写**——所有业务动作经 Action 引擎 `guard → 变更 → 写后校验 → 提交/回滚 → 审计`，**无旁路**。
4. **开源优先、薄适配**——自研只做"接缝"（五要素契约、SPI、Action 流水线）。
5. **多租户硬隔离**——一个 `ontology_id` ↔ 一个图库 space + 租户作用域。

> 第 1 条和第 5 条，就是第六节两仓分工的方法论来源。**学员把名录数据写进 plugins/，违反的不是习惯，是红线。**

### 10.6 方法论内核四：三层架构 Kernel / Plugin / Tenant

（机制 / 策略 / 实例三层分离）

| 层 | 归属 | 含行业词 | 内容 |
|---|---|---|---|
| **Kernel 内核（机制）** | clife，一次投入跨行业复用 | 否（CI 强制） | 元模型、Action 内核、规则引擎、回滚、审计、置信度、意图编译 |
| **Plugin 行业插件（策略）** | clife + 行业专家，每行业一份 | 是（隔离在插件内） | 五要素 Schema、映射、规则函数、Action handler、Agent、CQ |
| **Tenant 租户配置（实例）** | 客户，每客户一份 | 是（实例数据） | 私有物理映射、实例数据接入、密级与授权 |

内核与插件**只通过 `clife_onto_engine/sdk/`（Plugin SPI）通信**——**目录边界即红线**。

> **"本体即基础设施"**：内核只懂本体怎么运转、**不懂任何行业**。草业项目（草业）只是它的 tenant-zero，医疗 / 金融照样跑同一内核。

### 10.7 方法论内核五：元模型五要素 = 内核↔插件的唯一契约

内核只理解五种元类型，**任何行业概念都是插件用它们声明的实例**：

| 要素 | 定义 | 判据（现场问学员） |
|---|---|---|
| **Object** | 业务实体，有独立生命周期 | 有独立生命周期 / 独立属性 / 被引用？ |
| **Link** | 有向关系，带边语义 | 有方向吗？能带属性吗？ |
| **Function** | 只读派生量，**无副作用** | 是算出来的，不是记下来的？ |
| **Rule** | 全局不变式，违反则回滚 | **所有入口都要成立、且是操作后校验**（≠ 只判本次的前置条件） |
| **Action** | 受审计业务动作，有前置、有副作用、需留痕 | 有名字吗？要审计吗？带业务意图吗？ |

**Action 的写路径是这栈的灵魂**：

```
guard（前置 declarative）
  → stage_write（内存变更）
  → post_rules（写后强制，违反即回滚）
  → 提交 / 确定性回滚
  → 审计快照 + set_confidence 置信度 + add_evidence 证据
```

> `ctx` 是**受限 Capability，不是裸 context**——这就是第七节 `check_plugin_capabilities.py` 拦"内核私有直达"的道理。

**⚠️ 最容易讲漏的一条**：**Rule 与"前置条件"不是一回事。**前置条件只判本次调用；Rule 是全局不变式，**在所有入口、操作之后**都要成立，违反就回滚。学员写 §7 时经常把前置条件当规则写上去。

### 10.8 方法论内核六：建模 SOP——先把本体建模做对（`reference/methodology 03`）

这栈的方法论不止有概念，还有**可照做的建模 SOP**，是方法论文集里最实操的一篇：

**① 起点不是"有哪些数据"，是"现在的做法在哪出了问题、集中在哪个业务范围"。**
三类反复出现的问题：

| 症状 | 表现 |
|---|---|
| **信息没法汇聚** | 散在多系统，Agent 拿到不同时间点的拼凑结果 |
| **规则无法被执行** | Agent 走后端接口绕过了前端校验——**规则没失效，只是从没在这条路径上被执行过** |
| **决策无法还原** | 日志记的是接口调用，看不出"为什么代采购经理下了这笔 28 万的单" |

先界定问题 → 划 **MVP 边界**。

**② 基于业务语义（不是系统字段）推五要素。** 见 10.7 的五问。

**③ 先建模、再看数据——顺序不能反。**
先看数据会被现有系统结构带偏，建出"**系统长什么样**"而非"**业务是什么样**"。建完再逐属性追溯来源系统 + 治理（编号对照表 / PDF 解析管道 / 只导近两年有完整状态的记录）。

**④ 四阶段有先后、不并行：**

| 阶段 | 要点 |
|---|---|
| ① 调研与建模 | **业务专家必须在场，工程师单独做必跑偏**；产出**文档 / 原型不是代码**，业务逐条确认 |
| ② 数据盘点与治理 | |
| ③ 引擎搭建与数据接入 | **这一阶段才开始写代码** |
| ④ 场景验证与调优 | **Demo 的价值在暴露边界，不是证明对** |

**⑤ 怎么判断建对了——三问：**
① 信息汇聚实现没有？
② 规则真在执行没有？——**警惕误拦截 > 漏拦截**：持续误拦截会逼业务绕过本体，整套约束就失效。
③ 决策能不能当天说清楚？

> **金句直引（可直接板书）**：
> **"本体建模是把业务知识变成可执行定义的过程，而不是软件开发本身。最难的环节不是选技术栈，而是和业务人员一起把'大家都知道但没有人写下来'的规则，变成能被系统执行的精确描述。"**

### 10.9 与 Palantir 的关系（对标坐标，不是照抄）

OAG 概念出自 Palantir AIP；Palantir 的 Ontology 分**语义层**（Object / Property / Link）+ **动能层**（Action / Function / writeback），是"以本体为核心的企业智能操作系统"。

**C-Life 做的是这套语义 OS 的自有实现**——语义读（OQL 查受治理对象图）、治理写（Action 引擎）、审计快照、Explorer 展示、MCP 桥，**语义面全自有、不依赖外部脊椎**。

方法论文集 `06` 讲得更直白：**新型 FDE = 从第一性原理建领域模型 + 判断力 + AI 执行力**，"**本体不是 Palantir 的专利，是一种工程方法论**"。战场边界也和本课程一致——**探索 / 验证 / 新项目落地不可替代，规模化 / 组织推动瓶颈在人**（= 讲 3 的 C7）。

### 10.10 落到康养项目的真实插件：五要素到底长什么样（本节重点）

光讲 Palantir 的概念还是悬空的。看康养项目**真正编译出来的本体插件**——这是这门课区别于"传统信息化建模"的硬核。

**① 一域一插件，四个文件。** 7 个域各编译成一个 `clife-onto-engine` 插件骨架：

| 文件 | 内容 |
|---|---|
| `__init__.py` | 五要素的可运行声明（**只 import `clife_onto_engine.sdk`**，红线） |
| `mappings/objects.yaml` | 对象到数据源的映射 |
| `cq/golden.yaml` | 行为黄金问题（CQ，验收本体拦得住 / 放得过） |
| `plugin.yaml` | 插件元数据 |

7 域合计 **Object 76 / Link 75 / Function 38 / Rule 47 / Action 54 / HIL 26**，**3835 行纯 Python + 21 YAML，7/7 py_compile ✓**。
其中 Rule 47 = **声明式 18 + function 骨架 29**。

**② 五要素就是五种 SDK 构造。** 以 D1 `kangyang-agent-core`（10 对象 / 13 关系 / 5 函数 / 6 规则 / 6 动作 / **2 HIL**）为例：

- **Object → `ObjectType`**：如 `HealthInsight`（健康洞察）声明 `primary_key`、`properties`（每属性一条 `PropertySpec`，带类型 / 是否必填 / 密级 `classification="confidential"` / 单位）、状态机 `states=("new","triaged","addressed","closed")`。
  **跨域共享根 `Elder` 一律 `ref(Elder)` 引用，不在本域重复声明全属性**——这就是"对象只有一个真相源"的纪律。
- **Link → `LinkType`**：如 `root_caused_by`（洞察→根因，1:N），带 `edge_semantics`（`root_cause` / `hypothesis` / `derivation`）——**语义化的边，不是一根裸箭头**。飞轮再入用 `loops_back`（`hypothesis`，指向待续假设）。
- **Function → `FunctionDef`**：无副作用的计算，如 `plan_confidence`、`red_flag_count`、`opportunity_estimate`——**可重算，采纳才转 Action**。
- **Rule → `@spi.rule`**：分两类——`Backing.DECLARATIVE`（从 `check` 全自动、`source="通用"`、治理审计直接放行，如"方案须可解释""HIL 必留痕""链路顺序不可逆"）与 `Backing.FUNCTION`（需查图谱 / 跨对象的硬规则，如**"置信度闸·防橡皮图章"**、"药食 / DIP 冲突拦截"）。每条带 `severity=Severity.HARD`、`source` 和 **`citations`**（如 `DIP 技术规范(医保办发〔2020〕50号)` + `某地级市 DIP 控费实施细则[本地待补文号]`）——**挂得上的挂国标，挂不上的留占位不编造**，这就是栈⑦合规在本体层的落点。
- **Action → `@spi.action`**：对外副作用，`writes` 本域对象、`guards` 引本域规则；跨域**一律注释"发布到 D2/D3/D4"、不越界 `stage_write` 他域**。审批类动作挂 **`hil=HilPolicy(reviewer_role="站长", ...)`**——**这就是站长 HIL 增收闸在代码里的样子**（怎么设、设在哪，T5b 主讲）。

**③ 骨架 + 显式挂账。** 规则体 / 动作 handler / 派生函数留 `raise NotImplementedError("…待实现")`，**全域共 121 处**（29 function 规则体 + 54 Action 回写 + 38 Function 派生）+ 7 seed，交现场 FDE 在引擎仓库内填。

> **先跑通编译（可运行 > 完美），再填规则体。** 不确定的（如 SDK 是否导出 `Evaluation`）**显式落 docstring 挂账**，不靠"应该支持吧"——这就是第七节收尾清单第 6 项的由来（B-9）。

### 10.11 案例成熟度：别把方案说成交付（诚实分层，课上必须报口径）

| 案例 | 成熟度 | 到哪一步 |
|---|---|---|
| **康养项目** | 🟢 | **唯一全域编译交付**（7 域 / 3835 行 / 121 处挂账） |
| **草业项目** | 🟡 | 方案 + **11 页 Mock demo**（AI 是关键词路由，**不是真模型**）+ pilot 本体（`grass`：**7 对象 / 3 关系**） |
| **辣椒** | 🟡 | 方案 + pilot 本体（`chili`：**5 对象 / 0 关系**）· **无 demo** |
| **教育督导项目** | 🟢 | 建模 + **47 页 demo（数据真）** |

> ⚠️ **这张表的口径以本表为准**，讲义里若出现"草业项目本体未编译""辣椒 plugins 还是空的"之类的旧表述，**按本表更正**。
> **为什么非讲不可**：第八节让学员并排看 `grass`（3 条 Link）和 `chili`（0 条 Link）——**只建对象不建关系，本体就退化成一张数据字典**。成熟度分层不是谦虚，是**不把"有个 pilot 本体"说成"编译交付"**。

### 10.12 自学地图与自评（发给学员带走）

**首选教材**：`onto-fundary-plugins/reference/methodology/` 这套 **36 篇方法论文集**（"工程师的本体论"系列，自有、成体系）。阅读地图：

| 目的 | 篇目 |
|---|---|
| 打底认知 | `01 缺的不是数据，而是本体` · `02 决策系统的真正内核：本体模型` · `28 Software 3.0 的文件系统：本体` |
| **建模怎么做** | **`03 在动手之前，先把本体建模做对`**（三步建模法 + 四阶段顺序 + 三个判断）· `06 AI 时代的 FDE` |
| OAG 的本质 | `07 OAG 与 RAG 的分界` · `08 把 Schema 变成能力清单` · `09 Agent 以为成功了引擎在最后一刻回滚` · `10 三个月后你能回答 AI 为什么这样做` · `23 置信度总线` |
| 系统全貌 | `17 我们在构建什么：AI 原生 OS 内核` · `22 意图编译器` · `33 双本体联邦` |

配 `clife-onto-engine` README + `docs/01/02`；再读 **Palantir Foundry Ontology 官方文档**建对标坐标；最后对着康养项目某域 `ontology-map.md` + 编译产物 `__init__.py` **逐要素仿写**。

**自评到"能交付"的六条**：
- [ ] 能讲清 **OAG ≠ RAG**（防幻觉在执行层不在检索层）
- [ ] 能照 `03` 的三步 SOP 独立建一个域并**编译通过**
- [ ] 能对任一 Action 判"改哪个对象、走 guard / post_rule 哪道校验、是否回滚、是否设 `HilPolicy` 闸"
- [ ] 能分清一条规则该 `DECLARATIVE` 还是 `FUNCTION`
- [ ] 能区分"**规则 vs 前置条件**"
- [ ] 能说清 Kernel / Plugin / Tenant 三层"**行业词为什么不能进内核**"

---

---

## 十、实操（45′）

| 序 | 做什么 | 时长 | 产出 |
|---|---|---|---|
| 1 | 补完 `domain-intake` §3–§9（T1 已填 60%） | 20′ | 完整 intake，§7 至少 5 条规则 |
| 2 | `/studio-ontology:model {id}`，**在停点认真审 IR** | 20′ | `ontology-map.md` 七段 |
| 3 | 编译 + 数 NotImplementedError + 对照收尾 6 项 | 5′ | 骨架 + 收尾清单 |

**🔔 本步交付物**：`ontology-map.md` 七段 IR + 一份"哪 6 项要人做"的收尾清单。
**HIL 设点表与取证清单是 T5b 的产出**，本步只需在 IR 的 `hil` 列先留位。

> **45 分钟填不完 121 处 NotImplementedError，也不该填。** T5a 要学员带走的是**结构判断力**：什么是对象、什么是派生量、什么规则只看入参。

---

## 十一、checkout（20′）

| 维度 | 达标 | 警示 |
|---|---|---|
| 规则三问 | 每条 Rule 都答了 severity / backing / source | 有规则没标 backing |
| declarative 判定 | 需要查名录/阈值的都标成了 function | 把要查数据的标成 declarative → **一票警示** |
| check 方向 | 写的是"什么情况合法" | 写反成"什么情况拦截" |
| source 三态 | 有出处写标准号、常识写"通用"、查不到写 `TODO(FDE)` | **编一个像国标的号 → 一票警示（B-6/B-10）** |
| Link | 有关系、edge_semantics 判过 | links 为 0（本体退化成数据字典） |
| 收尾诚实 | 知道哪 6 项要人做，没假装编译完就能跑 | 以为 compile 完就结束了 |

---

## 十二、给讲师的时间盒（90′）

| 段 | 时长 |
|---|---|
| 开场"这不是编译器" + 四命令与权限边界 | 15′ |
| 知识注入 · 讲 4 栈③ OAG | 25′ |
| 七段 IR + 规则三问讲解 | 20′ |
| 实操（intake → model → 编译） | 45′ ← 与上面穿插 |
| FDE 收尾 6 项清单 | 10′ |
| checkout | 20′ |

**主持提示**：要砍就砍 IR 七段的逐段讲解（让学员照着 chili 示例自己看），**"收尾 6 项"绝不能砍**——它是诚实边界的具体落点。

---

## 十三、与下游的衔接

**下一步直接接 T5b**：拿着刚产出的 `ontology-map.md`，去给每个 Action 定闸、给每条规则补出处。

```
T5a 产物
  ↓ ontology-map.md 的 Action 列表  → T5b 逐个判"要不要设闸"
  ↓ 每条 Rule 的 source 三态         → T5b 治理审计与取证清单
  ↓ 编译骨架 + 收尾 6 项             → T5b 的 validate 校验对象
  ↓ ontology-map.md                  → T6 方案稿的"技术方案/本体设计"章
```

---

## 十四、讲师包 · 口播稿

### 本步用哪几个课件

> 课件在 `../slides/`，浏览器直接打开。**键盘 ← → 翻页 · S 演讲者模式 · O 总览。**

| 课件 | 用在哪一段 | 怎么用 |
|---|---|---|
| `slides/04b_知识栈_本体OAG详解.html` | 知识节·栈③ | **全用**（57KB，四分册里最厚的一本）。OAG≠RAG、五要素、五条设计红线 |

> ⚠️ **课件是旧十讲时期做的**，口径以本册为准——课件若与本册冲突（尤其案例成熟度、「合资」旧口径），**以本册为准，当场改口**。


> 以下为《第 4 讲 · FDE 的知识背景栈》的**讲述脚本原文**，供讲师直接照念，**不改写、不缩写**。
> 用法：第九节开讲前念第一段定调，栈③讲完念第二、三段收口，checkout 前念第四段。

### 口播 · 为什么是"角色合体"，不是"技能清单"

> "上一版这一讲我讲'五维知识栈'，讲浅了。今天换个讲法，也是更真实的讲法：你要成为 FDE，本质上是要**一个人干完过去七个岗位的活**。传统模式做康养项目这种项目，会议室里坐七种人——产品经理定需求、架构师切系统、知识工程师建图谱、商业顾问搭模式、财评专家算功能点、方案经理写标书、法务把红线。他们各说各的行话，交接处全是信息衰减（这就是第 1 讲的交付断层）。FDE 消除断层的办法，不是协调这七个人，是**把这七套方法论装进自己脑子**，一个人从头跑到尾。所以这一讲不是七个技能点，是**七个角色的方法论体系**，每一个我都给你一本业界压舱的经典——你补哪一栈，就去啃那一本。"

### 口播 · 本体建模不是软件开发本身（方法论 `03` 金句直引）

> **"本体建模是把业务知识变成可执行定义的过程，而不是软件开发本身。最难的环节不是选技术栈，而是和业务人员一起把'大家都知道但没有人写下来'的规则，变成能被系统执行的精确描述。"**

### 口播 · 会建模的人不会被替代（方法论 `06` 两句判断）

> **"AI 能把想清楚的事快速变成代码，但不能代替'想清楚'这件事本身"**；
> **"平台越来越便宜，本体模型越来越值钱——会建模型的人，不会被替代，而是被放大。"**

### 口播 · 难听话：建模只是七分之二

> "你以为 FDE 就是会建模？建模只是七分之二。你能交出 7 域本体、3835 行骨架——很好，那是栈②栈③。客户翻到可研最后一章问你'总投资多少、功能点怎么算的、IRR 几年回本'，你答不出某工业城市那样的'27,056 功能点 / 4,839 万'、答不出'15.2% 第 9 年回本'，你就只是个更贵的建模师，不是 FDE。缺的那五个角色，不会因为你建模漂亮就自动长出来。"
