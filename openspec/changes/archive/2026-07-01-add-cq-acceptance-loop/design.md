## Context

`ActionEngine(registry, store).validate(ont, action, params, actor) → ActionPreview(would_commit, violations)`（无副作用）。`oql.execute(q, QueryView(store,[]), registry) → OQLResult(rows, cost)`。CQ 验收 = 声明期望 + 用这两个执行器跑、判 pass/fail。

## Goals / Non-Goals

**Goals:** 声明式 CQ（动作期望裁决 + 查询期望行数），对某本体版本跑 pass/fail 报告；复用 validate/oql_execute（只读）；能抓能力回归。

**Non-Goals:** 不改 validate/oql；不做 NL→CQ（CQ 是结构化声明，NL 是建模端的事）；不做 CQ 自动生成（留建模端/C1）；查询 CQ 只判行数门槛，不做逐行精确断言（留扩展）。

## Decisions

### D1. 两类 CQ：动作期望裁决 + 查询期望行数
`ActionCQ(expect ∈ {commit,reject}, expect_rule?)`：跑 validate，pass = would_commit 与 expect 一致，且 expect_rule 给定时该规则 ∈ violations。`QueryCQ(oql, min_rows)`：跑 execute，pass = len(rows) ≥ min_rows。**备选**：只做动作 CQ——否，查询能力也需验收（本体"会查什么"）；但查询先只判行数门槛，保持轻。

### D2. 对指定 registry 跑 → 天然版本化验收
`run_cq_suite(cqs, registry, store)` 的 registry 可为活的或 `OntologyVersion.registry`。故同一套 CQ 能对不同版本跑 → 版本演进的**能力回归门**。**备选**：绑死活 registry——否，版本化验收是 C3 的核心价值。

### D3. 复用只读执行器，套件与本体分离
动作走 validate、查询走 oql_execute，均无副作用。CQ 套件由**插件/建模端**提供（如 `plugins/grass` 的 CQ），内核只提供 `run_cq_suite`——内核不含任何具体 CQ（行业无关）。

### D4. 结果结构
`CQResult(name, kind, passed, expected, actual, detail)`；`CQReport(total/passed/failed, results, summary)`。fail 的 detail 讲清期望 vs 实际（如"期望 reject·乡土合规，实际 commit"）。

## Risks / Trade-offs

- [动作 CQ 需 validate_supported] → 不支持则该 CQ fail 并注明（或 error），不静默。
- [function-backed 动作 CQ 依赖 store] → 同 replay 边界：调用方传相关 store（grass CQ 传 seeded）。
- [查询 CQ 只判行数] → 明确是门槛式验收；精确断言留扩展。

## Open Questions

- CQ 是否支持"期望某动作对某角色被权限拦"（actor 维度）？ActionCQ 已带 actor_role，天然支持（换角色即验权限）。
- 是否把 grass 的 CQ 套件放进 `plugins/grass`？倾向是（槽位7 CQ 验收集本就属插件），smoke/test 引用它。
