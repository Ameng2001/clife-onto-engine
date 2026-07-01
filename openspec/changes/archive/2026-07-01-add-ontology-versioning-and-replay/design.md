## Context

`Registry`（sdk/registry.py）是可变 dataclass：objects/links/functions/rules/actions/mappings，按 (ns,name) 键；有 `get_action/get_rule/get_function`。`ActionEngine(registry, store, audit, journal)` 从注入的 registry 解析。`validate(ont, action, params, actor) → ActionPreview`（无副作用，resolve 自 self.registry）。`AuditSnapshot` 有 ontology_id/action/actor_id/actor_role/inputs_snapshot/rules_evaluated/decision/schema_version。五要素 def 都是 frozen dataclass（含 impl callable 引用）。

## Goals / Non-Goals

**Goals:** 本体快照成不可变可寻址版本（可喂 engine）；用 AuditSnapshot 存的 inputs 只读重放 validate，复现/对比裁决 + 反事实 param 覆盖。行业无关、只读、版本不可变。

**Non-Goals:** 不做点位历史 store 快照（完全忠实时点重放）——留扩展；不做批量变更影响分析（B2 砖3）/CQ 回路（C3 砖4），本变更只出它俩的地基；不改 execute/validate/AuditSnapshot。

## Decisions

### D1. 版本 = 一个只含该本体定义的冻结 Registry
`snapshot_ontology(registry, ontology_id, version)` 新建一个 Registry，浅拷贝该 ns 的 objects/links/functions/rules/actions + 相关 mappings（五要素 def 是 frozen dataclass，拷引用即不可变）。返回 `OntologyVersion(ontology_id, version, registry)`。因版本 registry 就是个 Registry，`ActionEngine(version.registry, store=...)` 直接可执行——**零新执行路径**。**备选**：给 Registry 加内部版本字典——否，独立快照对象更清晰、天然隔离。

### D2. 不可变：快照后活 registry 变更不影响旧版本
快照持有的是当时的 def 引用集合；之后往活 registry 加/改注册，不进已快照的版本。测试断言：snapshot v1 → 活 registry 加个新 Action → v1 里查不到。

### D3. 重放 = 用存的 inputs 重跑 validate（复用无副作用执行器）
`replay(snapshot, registry, *, store=None, param_overrides=None)`：actor=Actor(snapshot.actor_id, snapshot.actor_role)；params={**inputs_snapshot, **(param_overrides or {})}；engine=ActionEngine(registry, store=store or InMemoryStore())；preview=engine.validate(...)。**备选**：另写重放执行器——否，validate() 已是无副作用预演，复用即忠实且零重复。

### D4. flipped 判定：原裁决 vs 重放 would_commit
`original_would_commit = snapshot.decision in {"committed","pending_hil"}`；`flipped = original_would_commit != preview.would_commit`。pending_hil 视为"会提交但需复核"，归入 would_commit=True 侧。ReplayResult 带 original_decision / replay_would_commit / flipped / violations / counterfactual(bool) / against_version。

### D5. function-backed 规则读调用方 store（范围诚实）
validate 的 guard（declarative）从 params/actor 复现——**总是忠实**。function-backed post_rule 读 store：重放用**调用方传入的 store**（默认空）。所以 declarative-only 决策空 store 即可复现；含 function-backed 的需传相关 store（如 grass 的 Site/NativeListing）。**点位历史 store** 留后续。文档/测试都讲清这条边界。

## Risks / Trade-offs

- [validate_supported=False 的 Action 无法重放] → replay 返回结构化 skip（原因），不抛。
- [function-backed 重放依赖 store] → D5 讲清；grass 测试传 seeded store 复现，空 store 测 declarative-only。
- [快照浅拷贝共享 impl callable] → def 是 frozen、impl 是纯函数（沙箱内），共享引用安全且正是"同一段规则逻辑"。
- [版本 registry 缺 mappings 导致 function-backed 找不到映射] → 快照带上该 ns 的 mappings。

## Open Questions

- 版本号策略：调用方给（如 `grass@0.2.0`）还是自动递增？倾向调用方给（与现有 schema_version 串一致），自动策略留建模端。
- 反事实是否也允许覆盖 actor（换角色重放看权限）？本期 param_overrides 先覆盖 params；actor 覆盖留小扩展（signature 已预留位）。
