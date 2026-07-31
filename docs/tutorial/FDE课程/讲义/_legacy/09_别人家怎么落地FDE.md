# 第 9 讲 · 别人家怎么落地 FDE（讲义 / 讲师用）

> 版本 v0.1 · 对象：C-Life 内部专业人员 · 实践蓝本：康养行业大模型平台
> 本文件是**讲师稿**：逐页要点 + 原话级讲述脚本 + 时间分配。学员动手材料在 `工作坊/09_别人家怎么落地FDE_workshop.md`。
> **本讲全部外部事实联网核证，逐条标来源；查不到写"未获证实"，绝不虚构。** 这不是免责声明，是本讲的教学主体——见反例 B-10。

---

## 〇、讲师须先读：本讲为什么"来源标注"比"信息量"更重要

这一讲讲的是 Palantir/OpenAI/Anthropic 怎么落地 FDE。学员天然想听"内幕"。但本讲真正要教的，不是这些公司的八卦，而是一件事：

> **当你要把外部实践当作论据时，你标注来源的严谨程度，等于你专业的可信程度。**

这和康养项目里"11 处地方文号查不到就留 `[本地待补文号]` 占位不编造"是**同一条纪律**（反例 B-10）。区别只是：那次取证对象是某市医保局的文号，这次取证对象是 Palantir 的招聘页。原则一模一样——**错的来源比空缺更有害**。

所以本讲义每一条外部事实后面都紧跟来源标注，且刻意区分三档：
- **【官方明确】** ——公司自己的博客/招聘页写的；
- **【二手报道】** ——分析机构/媒体/自媒体转述的；
- **【未获证实】** ——检索不到一手出处，或多方口径打架的。

讲师讲这一讲时，**必须把这三档亲口念出来**。你念的方式，就是学员将来对客户标注来源的方式。

---

## 一、一句话命题 + 能力模型定位

**命题：FDE 不是 C-Life 发明的，它有原产地（Palantir）、有前沿实验室的当代变体（OpenAI/Anthropic），也有国内水土不服的真实困境；把别人家看清楚，是为了知道我们能抄什么、什么抄不得。**

一句先撂在这里的话：
> **对标不是抄作业，对标是先证明你有资格抄——而资格的第一关，是你敢不敢在查不到时写"未获证实"。**

**能力模型定位**：本讲主打 **C4 合规治理**（来源取证 / 诚实边界），并回收全课程主张 3——"FDE 专业性一半体现在敢说不知道"。同时为第 10 讲（C-Life 怎么落地）提供外部参照系。

---

## 二、时间分配（90′，节奏 4 : 4 : 2）

| 段 | 占比 | 分钟 | 内容 |
|---|---|---|---|
| 认知输入（讲） | 40% | 36′ | 要点页 1–5（含 2·补）：FDE 原产地 Palantir / Delta×Echo 分工 / **我们一手对照(方法论06)** / 前沿实验室变体 / 国内困境 / 共性与差异 |
| 现场演练（练） | 40% | 36′ | Exercise「外部实践对标卡」 |
| 复盘研讨（议） | 20% | 18′ | 3 研讨题 + 收口 |

分钟级建议：页 1 Palantir 原产地（7′）→ 页 2 Delta×Echo 分工（6′）→ **页 2·补 我们一手对照 方法论06（5′）**→ 页 3 OpenAI/Anthropic（6′）→ 页 4 国内困境（7′）→ 页 5 共性差异+落回 C-Life（5′）→ 演练（36′）→ 研讨（18′）。

---

## 三、认知输入

### 要点页 1 · FDE 的原产地：Palantir 的 "Delta"

**【讲述脚本】**
"我们先回到源头。FDE 这个词不是硅谷 2026 年才火的新概念，它出生在 Palantir——一家长期给政府和大企业做保密数据整合分析的公司。Palantir 的解法很反常识：不把产品打包卖出去让客户自己用，而是**把工程师直接派到客户现场长期驻场**，在现场找瓶颈、搭原型、把平台配到能解决客户具体问题为止。

Palantir 官方博客对这个岗位的定义，我原话念给你们听——**【官方明确】**：'A Forward Deployed Software Engineer（FDSE），or "Delta," is a software engineer who embeds directly with our customers to configure Palantir's existing software platforms to solve their toughest problems.'（据 Palantir 官方博客《A Day in the Life of a Palantir Forward Deployed Software Engineer》，blog.palantir.com）

注意两个词：**embeds directly（直接嵌入客户）**、**Delta（内部代号）**。还有一句我认为最关键——**【官方明确】**：'While a traditional software engineer, or "Dev," focuses on creating a single capability that can be used for many customers, FDSEs focus on enabling many capabilities for a single customer.'（同上）

翻译成大白话：普通研发是'一个能力卖给很多客户'，FDE 是'很多能力喂给一个客户'。这句话你们记住，它就是 FDE 和产品经理的分水岭，也是我们康养项目做法的祖师爷定义。"

**【板书】**
```
Palantir FDSE = "Delta"
  · embeds directly with customers（现场嵌入）
  · Dev:  一个能力 → 很多客户
  · FDSE: 很多能力 → 一个客户   ← FDE 的基因
来源档位：【官方明确】blog.palantir.com
```

**【康养项目证据】**
康养项目就是"很多能力喂给一个客户"的活样本：不是卖一个通用养老 SaaS，而是为康养项目一地配出 7 域数智本体、五要素合计 Object 76 / Link 75 / Function 38 / Rule 47 / Action 54 / HIL 26、3835 行插件骨架。这正是 Palantir 定义里的 "many capabilities for a single customer"。**差异**：Palantir 派人长期驻客户机房；我们是 1 名 FDE 带智能体编队远程 + 短驻，用平台管线抵消了人数。

---

### 要点页 2 · 经典组织设计：Delta（FDE）× Echo（Deployment Strategist）分工

**【讲述脚本】**
"Palantir 最值得抄的不是岗位，是**岗位的配对设计**。它不是让一个 FDE 单打独斗，而是给 FDE 配了一个搭子，叫 **Deployment Strategist（部署策略师），内部代号 Echo**。

Palantir 官方博客怎么说这两者的分工——**【官方明确】**：Forward-Deployed Engineers（Deltas）负责技术上的'construction power（建造力）'，而 Deployment Strategists 决定'what should be built（该建什么）'、'why it is important（为什么重要）'、'to whom and how it should be delivered（交付给谁、怎么交付）'。（据 Palantir 官方博客《A Day in the Life of a Palantir Deployment Strategist》，blog.palantir.com）

用一句话概括这个分工——**【二手报道】**，招聘平台 Paraform 的总结很精炼：'The deployment strategist owns the "why" and "what," while the forward-deployed engineer owns the "how."'（据 Paraform 博客《Forward-Deployed Engineer vs. Deployment Strategist》，paraform.com）我把它标成二手，因为这句话不是 Palantir 官网原话，是招聘中介的提炼——但和官方博客口径一致，可以用，但要说清楚它是二手。

再补一个常被混淆的点：Palantir 内部还有 **FDSE（Forward Deployed Software Engineer）** 和 **FDE / Forward Deployed AI Engineer** 等不同挂牌。Palantir 招聘页（jobs.lever.co/palantir）确实同时挂着 'Forward Deployed Software Engineer' 和 'Forward Deployed AI Engineer' 两类岗位——**【官方明确：岗位存在】**（据 Palantir 官方招聘页 jobs.lever.co/palantir 的职位列表标题）。但两者职责的细粒度差别，我检索时**未能取到招聘页正文全文**（页面对自动抓取返回 403），所以**具体差异标：未获证实**。这里我故意不替你们脑补，这就是示范。"

**【板书】**
```
Palantir 的双人配对（关键组织设计）
  Delta = FDE      → owns "HOW"  技术建造力         【官方明确】
  Echo  = DS       → owns "WHY/WHAT/WHOM"  该建什么/为谁 【官方明确】
  "why/what" vs "how" 的提炼 → Paraform            【二手报道】
  FDSE vs FD-AI-Engineer 细分职责差别 →            【未获证实】
```

**【康养项目证据 / 落回 C-Life 的关键判断】**
Palantir 把"该建什么(Echo)"和"怎么建(Delta)"拆给两个人。**康养项目这次是一个 FDE 把两头都扛了**——既做认知萃取（102 事件 → 7 域，这是 Echo 的活），又做结构建造（本体编译、代码骨架，这是 Delta 的活）。
- **借鉴**：Echo/Delta 的分工是一张能力清单，提醒我们 FDE 必须同时具备"定义问题"和"实现方案"两组肌肉——正对应能力模型 C1（认知萃取）+ C2（结构建模）。
- **不适用/要警惕**：Palantir 有钱给每个客户配两个高薪人。C-Life 的现实是一人分饰两角，靠平台（Astra Studio）把 Delta 那半的手工活固化掉。所以我们不能照抄"配两个人"，只能照抄"两组能力都得有"。这也解释了第 8 讲那句"多数人第一次会停在 L1"——因为 Echo+Delta 两套肌肉，多数人只有一套。

---

### 要点页 2·补 · 我们自己对 Palantir FDE 的一手对照（`reference/methodology 06`）

**【讲述脚本】**
"前面讲的 Palantir Delta/Echo，是**外部事实**，我按官方/二手/未获证实分了档。这一页换个来源——**我们自己方法论文集里的一手观点**（`clife-onto-engine · reference/methodology 06《AI 时代的 FDE》`）。这不是检索来的，是我们自己写的，所以我不标'未获证实'，我标它是**我们的立场**。

它把 **Palantir FDE 和'新型 FDE'做了一张对照表**——注意，这正是我们这门课定义的 FDE：

| 维度 | Palantir FDE | 新型 FDE（我们要的） |
|---|---|---|
| 依赖的平台 | Foundry（**需采购**） | 基本工具链 + 其余靠辅助编程完成 |
| 核心技能 | 深度理解 Foundry + 领域建模 | **从第一性原理建模 + AI 工具执行 + 业务领域知识** |
| 交付速度 | 受平台部署周期限制 | **第一天对话，第二天出 Demo** |
| 适用战场 | 已采购 Foundry 的客户 | 探索 / 概念验证 / 新项目落地 |
| 瓶颈 | 平台能力边界 | 数据治理、组织推动的时间 |

**三个判断直接搬进这门课**：
1. **新型 FDE = 领域建模 + 判断力 + AI 执行力**——把'不知道'变成'精确定义' + 知道该做什么 + 用 AI 把定义变成可运行系统。这和第 3/4 讲的能力模型完全同构。
2. **'本体不是 Palantir 的专利，它是一种工程方法论'**——所以我们不必买 Foundry，也能做 Palantir 做的事（第 4 讲栈③ = 我们自有的 clife-onto-engine）。
3. **战场边界**：探索/验证/新项目落地 **✅ 不可替代**；规模化/组织推动/运维 **❌ 瓶颈在人，不是工具**——**这就是第 3 讲的 C7、第 8 讲的能力半径**：AI 能压缩建造时间，压缩不了数据治理和组织推动的时间。

金句直引（可板书）：**'平台越来越便宜，本体模型越来越值钱。会建模型的人，不会被替代，而是被放大。'**"

**【板书】**
```
Palantir FDE  vs  新型 FDE（本课程定义）      来源：方法论06（我们一手立场）
  依赖 Foundry(需采购)  →  基本工具链+辅助编程
  懂 Foundry+建模       →  第一性原理建模+判断力+AI执行力
  受部署周期            →  第一天对话·第二天Demo
  战场：已采购客户       →  探索/验证/新项目（规模化组织=瓶颈在人=C7）
"本体不是Palantir专利，是工程方法论" → 我们做自有 clife-onto-engine
```

**【与前页的关系（诚实边界）】** 前面 Delta/Echo 是**外部事实**（标了档）；这一页是**我们自己的方法论立场**（一手，但也要说清它是"立场"不是"行业公认"）。两者不冲突：Palantir 用双人 + 采购平台，我们用一人 + 自有平台达到同类交付——**这正是第 3 讲"一人公司 OPC"的外部印证**。

---

### 要点页 3 · 当代变体：前沿实验室 OpenAI / Anthropic 怎么做 Forward Deployed

**【讲述脚本】**
"FDE 这两年重新火，是因为大模型来了。原来 Palantir 卖的是数据分析平台，现在 OpenAI、Anthropic 卖的是前沿模型——但它们遇到了和 Palantir 一样的问题：**模型放在 API 里客户用不起来，得有人把它落进客户的真实业务里**。于是这两家也建了 Forward Deployed 团队。

先看 **OpenAI**。OpenAI 官网 careers 页确实设了这个岗——**【官方明确：岗位存在】**，标题就叫 'Forward Deployed Engineer (FDE)'，有 SF、NYC、Tokyo、Gov（华盛顿）等多个坑（据 OpenAI 官方招聘页 openai.com/careers）。职责概括是——'embeds directly with OpenAI's most strategic enterprise and government customers to take frontier models from a demo into a live, working production system'，并且 own 从 discovery、scoping、system design、build 到 production rollout 的全过程（据 OpenAI 官方招聘页职位摘要 openai.com/careers；**注意**：我检索时官网正文对自动抓取返回 403，这段摘要来自搜索引擎对官方页的索引 + 二手指南 fde.academy 转述，所以我把职责措辞标为**【官方明确岗位存在 + 二手转述职责】**）。

关于 OpenAI FDE 的薪资——网上流传 35 万到 55 万美元总包、资深超 60 万——**这个我标【未获证实】**。因为唯一给出数字的来源（fde.academy）自己写明'these figures are compiled from Levels.fyi and industry comp reports'，不是 OpenAI 官方薪资表。**流传的数字不等于官方数字，这一步不能省。**

再看 **Anthropic**。Anthropic 把这个团队叫 **Applied AI**，岗位全称 'Forward Deployed Engineer, Applied AI'——**【官方明确】**，职责原话我念（据 Anthropic 招聘 JD，经 Menlo Ventures 招聘板 jobs.menlovc.com 转发官方职位）：
- 'Work within customer systems to build production applications with Claude models'
- 'Deliver technical artifacts for customers like MCP servers, sub-agents, and agent skills'
- 'Provide white glove deployment support for Anthropic products in enterprise environments'
- 'Identify and codify repeatable deployment patterns and contribute insights back to our Product and Engineering teams'
- 'Travel frequently (25-50%) to customer sites to build in person with customers'

薪资，这里有个**教科书级的打架案例，我专门留给你们看**：同一岗位，Menlo 招聘板转发的官方 JD 写年薪 **$200,000–$300,000 USD（base）**；而另一家分析媒体（getperspective.ai）写 total comp 落在 **$350K–$550K**。**两个数字都存在，但口径不同（base vs total comp），且后者是二手**。正确的标注是：base 区间 $200K–$300K【官方明确（经招聘板转发）】；$350K–$550K 总包【二手 / 未获证实为官方】。**如果你只抄一个数字不写口径，你就在制造错误。**"

**【板书】**
```
前沿实验室的 Forward Deployed 变体
OpenAI:    岗位=Forward Deployed Engineer (FDE)   【官方岗位存在】
           职责: demo → production，own 全流程     【官方+二手转述】
           薪资 35-55万刀总包                       【未获证实·Levels.fyi二手】
Anthropic: 团队=Applied AI；岗=FDE, Applied AI      【官方明确】
           产出物: MCP servers / sub-agents / skills【官方明确·可直引】
           出差 25-50% 到客户现场                   【官方明确】
           base $200-300K【官方(招聘板转发)】 vs 总包$350-550K【二手·口径不同】
```

**【康养项目证据 / 对照】**
Anthropic 的 JD 里有一条和我们高度同构——'Identify and codify repeatable deployment patterns and contribute insights back to Product and Engineering'（把现场可复用模式沉淀、反哺产品）。康养项目这次也在做同一件事：把交付过程沉淀成 `_WRITING_BRIEF.md`、SOP、反例库 B-1…B-10，这就是"codify repeatable patterns"。**差异**：Anthropic 反哺的是 Claude 的产品团队；我们反哺的是 Astra Studio 这条内部管线和这门课本身。方向一致，对象不同。

---

### 要点页 4 · 国内尝试：为什么"交付即研发"在中国普遍水土不服

**【讲述脚本】**
"现在把镜头转回国内。学员最该关心的是：这套东西在中国的 To-G/To-B 能不能成？我先给结论：**国内在'招 FDE'这件事上有真实动作，但在'FDE 模式能否跑通'这件事上，公开信息普遍是悲观的，且很多细节我查不到。**

**有动作的部分【官方岗位存在 / 二手】**：腾讯云确实在招'前线部署工程师（FDE）'这类岗位，多篇报道与其开发者社区文章提及（据腾讯云开发者社区 cloud.tencent.com 相关文章、知乎专栏转述）。网传腾讯云上海 FDE 岗 35-65K×15 薪——**这个薪资数字我标【未获证实】**，出处是知乎/招聘平台转述，非腾讯官方薪酬公告。

**悲观判断的部分【二手报道·观点】**：虎嗅有一篇《万字解读 FDE 为什么在中国是扯淡的》（作者 AI Humanist by 杉森楠，huxiu.com），列了几条障碍，我念给你们，但要说清楚**这是媒体作者的观点，不是行业统计定论**：
- 商业模式相反：'中国强制要求标准技术服务项目采用最低评标价法，客户只愿为成品付费'——探索/试错的成本默认由乙方承担；
- 人才鄙视链：文章称'应届生交付岗年薪仅 10-15 万，同级别大厂研发达 30-55 万'，顶尖人才流向大厂；
- 甲方不真信 AI：文章引'95% 的企业 AI 试点失败'等数字。**注意：这些具体百分比我未能核到原始出处，标【未获证实】，讲课时必须连同'这是文章里的数字、我没核到源'一起说。**

还有一类声音直接把中国版 FDE 等同于老概念——'国内从早年的 ERP 实施、驻场顾问到驻场开发，已经做了 30 年 FDE 的核心业务，只是一直把这个工种叫外包'（据多篇国内自媒体/腾讯云社区文章的共同表述，属**【二手报道·业界普遍认为】**）。

**总结这一页的检索纪律**：国内这块，**岗位在招是真的（可查到招聘挂牌），但薪资数字、成败结论、具体百分比大量属于二手甚至未获证实**。这正是本讲要教的——你越是想用一个数字支撑观点，越要先问'这个数字的一手出处在哪'。"

**【板书】**
```
国内现状（检索纪律示范）
  ✓ 腾讯云在招"前线部署工程师(FDE)"        【官方岗位存在/二手】
  ? 腾讯云 35-65K×15薪                       【未获证实·招聘平台转述】
  ~ "最低评标价法致乙方承担试错成本"         【二手·媒体观点·可信度较高】
  ? "95%企业AI试点失败""41%低于合理成本"等   【未获证实·数字未核到一手源】
  ~ "中国版FDE≈干了30年的外包换皮"           【二手·业界普遍认为】
结论：岗位真、模式存疑、数字大多不可当事实用
```

**【康养项目证据 / 落回 C-Life】**
虎嗅那条"甲方只为成品付费、不为探索过程付费"，恰恰是 C-Life 要正面面对的**中国 To-G 现实约束**。我们的应对不是"派人长期驻场熬成本"（那正是国内跑不通的点），而是**用平台把探索过程的成本压到极低**——康养项目 1 人 + 智能体编队完成传统 5+ 人数周的活，本质上是把"甲方不肯付费的探索成本"用工程化平台消化掉了。**这是 C-Life 相对 Palantir 模式的本土化改造，也是第 10 讲的伏笔。**

---

### 要点页 5 · 别人家的共性与差异，一张表落回 C-Life

**【讲述脚本】**
"最后收口。把 Palantir、OpenAI、Anthropic、国内放在一起，抽三条共性、三条差异。

**共性（可借鉴）**：
1. **现场嵌入、产品级交付**——都不是'写报告给建议'，而是把东西真正跑进客户生产环境。Palantir 'embeds directly'、OpenAI 'demo → production'、Anthropic 'build production applications'，口径一致【均官方明确】。
2. **把现场经验反哺回产品/方法**——Anthropic 'codify repeatable patterns'，这和康养项目沉淀 BRIEF/SOP 同构。
3. **强调现场取证、不臆造客户环境**——这是我最想让你们记住的一条，也是反例 B-10 的呼应，下一段专门讲。

**差异（不能照抄）**：
1. **客户体量**：Palantir/OpenAI/Anthropic 主打 Fortune 500、政府、战略级大客户，钱多、能配双人（Delta+Echo）。C-Life 是 **To-G 康养 + 微康养网络**，甲方是地级市国资/民政/医保，预算受最低价约束，只能一人分饰多角靠平台补。
2. **人 vs 平台的比例**：他们靠堆高薪人才驻场；我们靠 Astra Studio 把 Delta 那半固化，用更少的人扛更长的链条。
3. **薪资与人才市场**：硅谷 FDE 总包几十万美元、能和研究岗抢人；国内交付岗在鄙视链底端（前述【二手/未获证实】）。这决定了 C-Life 不能靠'招现成 FDE'，只能靠'选人 + 训练 + 平台'自造，这正是第 10 讲的主线。

一句话落地：**Palantir 教我们 FDE 该有哪两组肌肉（Echo+Delta）；前沿实验室教我们大模型时代 FDE 交付什么（production + 反哺）；国内的水土不服教我们哪条路不能走（堆人驻场）。三者合起来，指向 C-Life 唯一可行的路——工程化平台 + 一人多角。**"

**【板书 / 图】**
```
                 共性(抄)                    差异(不抄)
Palantir     现场嵌入·Delta×Echo双肌肉      配双人·大客户·驻场
OpenAI       demo→production·全流程own      战略客户·总包几十万刀
Anthropic    codify patterns 反哺产品        Fortune500·出差25-50%
国内         岗位真在招                       最低价/鄙视链→堆人驻场跑不通
─────────────────────────────────────────────────────────
C-Life 取舍：抄"两组肌肉+production+反哺"，弃"堆人驻场"，改"平台+一人多角"
```

> 配图（可选，浅色系占位）：本讲不强制配图。若配，建议一张四列对照的浅色系表格图，slug 未在总纲 figures 表登记，**按纪律不自造 slug、不调 fireworks**，留文字表即可。

---

## 四、现场演练导入（过渡话术）

"讲完别人家，现在轮到你们做取证。我给你们发一份**真实检索到的岗位 JD 片段**，每段都带来源，也**故意混进了一些我标了'未获证实'的说法**。你们要做一张《外部实践对标卡》：逐维度把 Palantir FDE 和 C-Life FDE 摆在一起比，并且——这是评分重点——**把哪些信息是'未获证实'的当场标出来**。

记住：这张卡我不主要看你比得多全，我看你**有没有把二手当官方、有没有把网传数字当事实**。这就是 B-10 那句'错文号比空缺更有害'的当代版：**错来源比空缺更有害**。现在翻开工作坊。"

---

## 五、复盘研讨（18′，3 题）

1. **分工题**：Palantir 用 Delta(FDE)+Echo(DS) 两个人分担"how"和"why/what"。康养项目让一个 FDE 把两头都扛了。这说明"C-Life 的 FDE 门槛比 Palantir 的 FDE 更高"，还是"平台把一部分门槛消化了"？你在自己项目里，哪一半（定义问题 / 实现方案）更是短板？
   - **收口**：门槛不是更高或更低，是**结构不同**。Palantir 用组织（两个人）解决，C-Life 用平台 + 一人多角解决。承认自己缺哪半肌肉，比嘴硬说都会更专业——这就是第 8 讲"装 L2 才危险"。

2. **取证题**：本讲哪些数字我标了"未获证实"？如果客户方案里你要引用"OpenAI FDE 年薪 50 万美元"来佐证"FDE 值钱"，你会怎么标注才算专业？
   - **收口**：至少要写成"据 Levels.fyi 等第三方薪酬报告（非 OpenAI 官方），约 35-55 万美元总包，口径未经官方证实"。**给数字 + 给出处档位 + 给口径 + 给不确定性**，四件套缺一不可。这和康养项目 11 处文号留占位是同一个动作。

3. **本土化题**：国内"甲方只为成品付费、不为探索过程付费"（虎嗅，二手观点）如果属实，C-Life 的应对是"堆人驻场"还是"平台压成本"？说出你的理由，并指出这条国内判断你有没有核到一手来源。
   - **收口**：答案指向平台压成本（康养项目 1 人 vs 传统 5+ 人已证）。但更重要的是——**很多人会忘了顺带说"虎嗅那条我没核到一手源"**。谁主动补了这句，谁就 get 到了本讲。

---

## 六、本讲难听话 + 反例讲解

**【本讲难听话】**
> "你觉得'查不到就写未获证实'很简单？那你回顾一下这堂课——我念了十几条外部事实，你能当场分清哪条是官方、哪条是二手、哪条是网传吗？分不清，你就没资格拿 Palantir 给客户站台，你只是在转发朋友圈。"

**【反例讲解 · B-10：11 处地方文号无解 → 对标 Palantir 的现场取证文化】**

康养项目里，有 7 处本地文号（本地 DIP 细则、助餐补贴办法等）+ 4 处企业 SOP 编号，**公开渠道查不到**。当时的处理不是编一个"看起来像"的文号糊过去，而是：留 `[本地待补文号]` 占位 + 锚定上位国标 + 转成一份向某市医保局/民政局/政数局逐项取件的清单。内部原话：**"错文号比空缺更有害。"**

这一讲把 B-10 抬到了第三次出现（第 3 讲、第 6 讲、本讲），是**复调不是重复**。本讲要点破的是它和 Palantir 的深层同构：
- Palantir FDSE 官方定义强调 'embeds directly'、在客户现场把问题**取证清楚**再建，不靠远程臆想客户环境（据 blog.palantir.com FDSE 博客）；
- 康养项目留占位、转取件清单，是**在自己的交付里对客户环境取证到底、不臆造**；
- 本讲你们做对标卡时标"未获证实"，是**对外部实践取证到底、不臆造**。

三者是同一种职业本能：**FDE 的可信度，建立在"敢承认取不到证"这件事上。** Palantir 的 FDE、康养项目的 FDE、你手里的对标卡，用的是同一条纪律。谁在这条纪律上偷懒，谁的方案就经不起客户一句"这个数据哪来的"。

---

## 七、与其他讲的钩子

- **← 第 3 讲（OPC 边界）**：本讲 Palantir 的 Delta×Echo 分工，正是第 3 讲"一人公司边界"的外部印证——别人用两个人的活，我们用一人 + 平台。
- **← 第 8 讲（什么样的人能成为 FDE）**：本讲证明"Echo+Delta 两组肌肉多数人只有一组"，呼应第 8 讲"多数人第一次停在 L1、装 L2 才危险"。
- **→ 第 10 讲（C-Life 怎么做）**：本讲的"共性抄什么、差异弃什么"直接喂给第 10 讲的落地路径——弃堆人驻场、走平台 + 选人训练自造 FDE。
- **↔ 反例 B-10（第 3/6/9 讲复调）**：本讲是 B-10 的价值观收束点——把"不编造文号"升级为"不编造来源"。

---

## 附：本讲外部来源清单（讲师备查，档位已标）

| # | 事实 | 档位 | 出处 |
|---|---|---|---|
| 1 | FDSE="Delta"，embeds directly，"many capabilities for a single customer" | 官方明确 | Palantir 官方博客《A Day in the Life of a Palantir Forward Deployed Software Engineer》 blog.palantir.com |
| 2 | DS="Echo"，Delta 负责 construction power，DS 定 what/why/whom | 官方明确 | Palantir 官方博客《A Day in the Life of a Palantir Deployment Strategist》 blog.palantir.com |
| 3 | "DS owns why/what, FDE owns how" 的提炼 | 二手报道 | Paraform《Forward-Deployed Engineer vs. Deployment Strategist》 paraform.com |
| 4 | Palantir 同时挂 FDSE 与 Forward Deployed AI Engineer 岗位 | 官方明确(岗位存在) | Palantir 招聘页 jobs.lever.co/palantir |
| 5 | FDSE 与 FD-AI-Engineer 细分职责差异 | 未获证实 | 招聘页正文抓取返回 403，未取到全文 |
| 6 | OpenAI 设 Forward Deployed Engineer (FDE) 岗（SF/NYC/Tokyo/Gov 等） | 官方明确(岗位存在) | OpenAI 招聘页 openai.com/careers |
| 7 | OpenAI FDE 职责：demo→production、own 全流程 | 官方岗位存在 + 二手转述 | openai.com/careers（官网正文 403）+ fde.academy 转述 |
| 8 | OpenAI FDE 薪资 35-55 万美元总包 | 未获证实 | fde.academy 自述引自 Levels.fyi / 行业薪酬报告，非官方 |
| 9 | Anthropic Applied AI 的 FDE 职责（MCP/sub-agents/skills、出差25-50%） | 官方明确 | Anthropic JD，经 Menlo Ventures 招聘板 jobs.menlovc.com 转发 |
| 10 | Anthropic FDE base $200K–$300K | 官方明确(招聘板转发) | 同上 jobs.menlovc.com |
| 11 | Anthropic FDE 总包 $350K–$550K | 二手/口径不同 | getperspective.ai（total comp 口径，非官方 base） |
| 12 | 腾讯云在招"前线部署工程师(FDE)" | 官方岗位存在/二手 | 腾讯云开发者社区 cloud.tencent.com、知乎专栏转述 |
| 13 | 腾讯云上海 FDE 35-65K×15薪 | 未获证实 | 招聘平台/知乎转述，非腾讯官方薪酬公告 |
| 14 | 中国 FDE 模式障碍（最低价、鄙视链、95%试点失败等） | 二手报道·部分数字未获证实 | 虎嗅《万字解读FDE为什么在中国是扯淡的》huxiu.com |
| 15 | "中国版 FDE≈干了30年的外包换皮" | 二手·业界普遍认为 | 多篇国内自媒体/腾讯云社区文章共同表述 |
| — | FDE 概念综述条目 | 参考(百科·非一手) | 维基百科 "Forward Deployed Engineer" en.wikipedia.org |

> 讲师提示：上表第 5、8、13 行以及第 14 行的百分比，**讲课时必须亲口说"这条未获证实/未核到一手源"**。你怎么念，学员将来就怎么对客户标注。
