# decision-replay Specification

## Purpose
TBD - created by archiving change add-ontology-versioning-and-replay. Update Purpose after archive.
## Requirements
### Requirement: 用审计快照只读重放决策
系统 SHALL 提供 `replay(snapshot, registry, *, store=None, param_overrides=None)`：从 `AuditSnapshot` 重建 actor（actor_id/role）与 params（inputs_snapshot），对给定 registry（活的或某版本）跑 `validate`，返回 `ReplayResult`（含 original_decision、replay_would_commit、flipped、violations、counterfactual、against_version）。重放 MUST **只读**（复用 validate 的无副作用，永不落库）。

#### Scenario: 复现原裁决
- **WHEN** 对一个记录为 committed 的 grass 决策，用当时同版本 registry + 相关 store 重放
- **THEN** replay_would_commit=True，flipped=False（复现）

#### Scenario: 反事实 param 覆盖翻转裁决
- **WHEN** 对同一决策用 `param_overrides={"species":["紫花苜蓿"]}`（非乡土）重放
- **THEN** replay_would_commit=False，flipped=True，violations 含"乡土合规"

### Requirement: 对不同本体版本重放，裁决随规则变
`replay` 对不同 `OntologyVersion` 运行时 SHALL 反映该版本的规则——同一决策在规则不同的版本上可得不同裁决。

#### Scenario: 换版本换裁决
- **WHEN** 同一决策分别对 v_old 与 v_new（规则更严）重放
- **THEN** 两次 ReplayResult 的 replay_would_commit 可不同（体现规则版本差异）

### Requirement: 不可重放动作结构化跳过
对 `validate_supported=False` 的 Action，`replay` MUST 返回结构化 skip（含原因），不抛异常。

#### Scenario: 不支持预演的动作
- **WHEN** 重放一个 validate_supported=False 的 Action
- **THEN** ReplayResult 标记 skipped 并给出原因，流程不崩

### Requirement: 重放范围边界（function-backed 依赖 store）
`replay` 的 guard（declarative）SHALL 从存储 inputs 忠实复现；function-backed 规则读**调用方传入的 store**（默认空）。忠实的点位历史 store 重放不在本能力范围（留扩展），文档 MUST 讲清该边界。

#### Scenario: declarative-only 空 store 可复现
- **WHEN** 重放一个只含 declarative guard 的决策、不传 store
- **THEN** guard 裁决忠实复现（不因缺 store 而误判）

