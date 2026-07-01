## Context

`Registry` 键为 (ns,name)：objects/links/functions/rules/actions。ActionDef 有 impl/guards/post_rules/writes；RuleDef 有 impl/source；LinkType 有 from_type/to_type；FunctionDef 有 impl。gap 审计 = 静态遍历该 ns 的定义，找结构悬空与治理缺口。

## Goals / Non-Goals

**Goals:** 静态审计某本体的 blocking（结构性会炸）与 advisory（治理文档缺）缺口，精确定位。只读、行业无关。

**Non-Goals:** 不"填"stub（codegen 回填在建模端）；不做运行时执行探测（纯静态）；不重复 OKF 的引用可视化（只报 source 缺口）。

## Decisions

### D1. 两级：blocking（结构）vs advisory（治理完整）
blocking 会在运行时导致解析失败/无法执行，必须修：Action.impl=None、guard/post_rule/writes 引用悬空、Function.impl=None、Link 端点对象不存在。advisory 不阻断执行但治理不全：Rule.source=""。`GapReport.ok = 无 blocking`（advisory 不影响 ok）。**备选**：一锅端——否，declarative guard 常无 source，混进 blocking 会噪音淹没真问题。

### D2. 只扫本 ontology 的定义
按 ns==ontology_id 过滤；引用检查在该 ns 内解析（guard/post_rule 名 ∈ 该 ns rules；writes ∈ 该 ns objects；link 端点 ∈ 该 ns objects）。

### D3. Gap 结构可定位
`Gap(kind, subject, detail)`：kind 如 action_no_handler/dangling_rule_ref/dangling_write/function_no_impl/dangling_link_endpoint/rule_no_source；subject=具体名；detail=人读说明。

## Risks / Trade-offs

- [declarative guard 无 source 报太多 advisory] → 归 advisory 不阻断；文档说明"guard 常无标准出处，按需补"。
- [跨 ns 引用误判] → 只在本 ns 解析；跨 ns 联邦引用不在本审计范围（留扩展）。

## Open Questions

- 是否也报"对象无属性声明"/"规则无 message_template"？倾向不——非结构性、噪音大，留扩展。
