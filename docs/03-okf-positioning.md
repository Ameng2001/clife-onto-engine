# OKF 定位 —— 规则的"权威文档/出处/版本层"，不是规则执行层

> 背景：Google Cloud 2026-06 开源 **OKF（Open Knowledge Format）v0.1**——用"带 YAML frontmatter 的
> Markdown 文件夹 + git"表示精炼知识，做 AI 时代知识喂给 Agent 的"通用语"。
> 仓库：https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf
>
> 我们用得到 OKF，但**必须放对层**——别犯和 RAG/OAG 一样的混淆。

---

## 0. 一句话定位

**OKF 是知识沉淀/文档层（读、静态、精炼）；规则的强制仍在 OAG 执行引擎。二者互补，不替代。**

OKF 官方就把自己定位成与 **MCP（实时工具/活数据，写）互补的知识层（读）**。按同一逻辑，
OKF 与 **OAG（受治理的写/执行）也是互补**：OKF **描述**规则（依据、出处、版本），引擎 **强制**规则。

> 判别口诀：**OKF 描述规则，引擎强制规则。别让 OKF "跑"，别让规则只躺在引擎里没文档。**

---

## 1. OKF 是什么（够用版）

- 一个知识包(Bundle) = 一个 git 文件夹；每个 `.md` = 一个概念（对象/指标/规则/手册…）。
- 唯一必填 frontmatter 字段：`type`；其余（title/description/resource/tags/timestamp）可选。
- 文件路径(去 `.md`)=概念 ID；md 链接=无类型有向边；外部来源放 `# Citations`。
- 保留文件：`index.md`（渐进式探索目录）、`log.md`（变更史）。
- 消费者**必须容忍**未知 type / 缺失字段 / 断链——格式随知识生长。
- 三层堆叠：`llms.txt`(入口/路标) → `EntityMap`(声明实体关系) → **OKF**(内容本身/图书馆)。

---

## 2. 在本仓库用得到的地方（读/文档侧）

治理规则要"规范"，缺的正是一个**权威、可审计、可 git diff、可被别的 Agent 消费**的规则文档层。OKF 正好补上：

| 用途 | 怎么用 |
|---|---|
| **规则出处与版本** | 每条 Rule 一个 OKF 概念：frontmatter 放机器字段(severity/backing/source)，正文放依据，`# Citations` 列标准/方法学；`log.md`+git 记演进 → 落地"来源可查 + 配置即 PR + 专家可审" |
| **本体可浏览/可审计** | 把 registry 的对象/关系/规则/动作导成 OKF 包，业务专家与 Agent 都能读；md 链接天然成图 |
| **互操作 + 开源优先** | 用 Google 正在标准化的格式导出，别家工具/Agent 直接消费，不锁定 |
| **治理缺口审计** | 导出时，无 `citations` 的规则自动标注"尚无文档化依据，待补"——一眼看出哪些规则缺依据 |

---

## 3. 不该用的地方（别把它当执行层）

- **别用 OKF 表达或运行规则逻辑**：guard、写后规则、function-backed 约束、回滚——必须留在引擎（`kernel/`）。
  OKF 是 prose+frontmatter，不可执行；它承载规则的**说明/出处**，不承载**强制**。
- **别用 OKF 替代能力清单 / Action 引擎**：那是 OAG（受治理的写）。OKF 是读。
- 一句话：OKF 进来的是"规则为什么这么定"，不是"规则怎么拦"。

---

## 4. 我们恰好补了 OKF 自己的公开缺口（互补，不是单向依赖）

OKF v0.1 官方承认未解决三件事——而我们的引擎正好都有：

| OKF 公开缺口 | 本仓库对应能力 |
|---|---|
| 矛盾/冲突处理（多方维护同一事实分歧） | HIL 冲突消解 + 置信度打分（knowledge-curator）、规则变更级联作废 |
| 时效性（静态文件谁更新、更新多频） | schema 版本治理 + 配置即 PR + 记忆生命周期/淘汰 |
| `type` 无中央注册（跨组织互操作障碍） | 我们的导出用固定 `type`（ontology-object/link/rule/action/function），自带约定 |

**所以：OKF 是我们缺的"作者/可移植格式"，我们是 OKF 缺的"治理/执行层"。**

---

## 5. 落地实现

- 规则加出处字段：`RuleDef.source` / `RuleDef.citations`（`spi.rule(..., source=, citations=)`）。
- 导出器：`clife_onto_engine/okf.py` 的 `export_bundle(registry, ontology_id, out_dir)` —— registry → OKF v0.1 包
  （对象/关系/规则/动作/函数各一概念 + `index.md`，规则带 `# Citations`，跨链接用 bundle-relative）。
- 跑：`python scripts/export_okf.py` → `build/okf/<ontology>/`，并自检 OKF 合规性 + 暴露治理缺口。
- 与行业无关、内核纯净：导出器只读 registry 渲染，不含行业词汇（CI 强制）。

> 关联：[`docs/02-oag-positioning.md`](02-oag-positioning.md)（OAG vs RAG/Skill 的层次纪律，与本文同源——别把不同层的东西混为一谈）。
