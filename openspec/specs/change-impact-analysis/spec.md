# change-impact-analysis Specification

## Purpose
TBD - created by archiving change add-change-impact-analysis. Update Purpose after archive.
## Requirements
### Requirement: 对一批决策做规则变更影响分析
系统 SHALL 提供 `change_impact(snapshots, old_registry, new_registry, *, store=None) → ImpactReport`：对每个历史决策的 inputs，用**同一 store** 分别对旧/新版本 `replay`，按翻转方向归类。同 store/同 inputs 保证差异**只来自版本（规则）变更**。

#### Scenario: 更严版本列出被新拦的决策
- **WHEN** 一批含 budget=300 的 committed 决策，new 版本把预算门槛改为 ≥500
- **THEN** ImpactReport 的 newly_blocked 含这些决策，每条带触发规则「预算非负」；unchanged 不含它们

#### Scenario: 更宽版本列出被新放的决策
- **WHEN** 一批原 rejected（预算<500）决策，new 版本把门槛放宽
- **THEN** ImpactReport 的 newly_allowed 含这些决策

#### Scenario: 无变更则全 unchanged
- **WHEN** old 与 new 版本规则相同
- **THEN** 所有决策归 unchanged，newly_blocked/newly_allowed 为空

### Requirement: 报告结构与触发规则
`ImpactReport` SHALL 含计数（total/unchanged/newly_blocked/newly_allowed/skipped）与每条翻转明细（本体/动作/方向/触发规则）。任一侧不可重放的决策 MUST 归 skipped，不影响其余。

#### Scenario: 报告可读计数与明细
- **WHEN** 分析完成
- **THEN** 报告给出各类计数，且每条翻转能读出是哪条规则导致

#### Scenario: 不可重放决策被跳过
- **WHEN** 某决策的动作 validate_supported=False
- **THEN** 该决策归 skipped，其余决策照常分析

