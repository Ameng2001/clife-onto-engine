## 1. 变更影响分析

- [x] 1.1 `clife_onto_engine/change_impact.py`：`change_impact(snapshots, old_registry, new_registry, *, store=None) → ImpactReport`——每条对 old/new 各 replay（同 store），比较 would_commit
- [x] 1.2 归类：newly_blocked（旧 commit→新 reject，带 new violations）/ newly_allowed（旧 reject→新 commit，带 old violations）/ unchanged / skipped
- [x] 1.3 `ImpactReport`：计数 + flips 明细（ontology/action/direction/triggering_rules）+ summary

## 2. 测试 + smoke

- [x] 2.1 `tests/test_change_impact.py`：更严版本→newly_blocked+触发规则；更宽→newly_allowed；无变更→全 unchanged；skip
- [x] 2.2 `scripts/smoke_change_impact.py`：一批 grass 决策对"预算≥500"版本 → 报告列被新拦的决策 + 触发规则

## 3. 收尾

- [x] 3.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 3.2 README §16 路线图勾上「规则变更影响分析（B2）」
- [x] 3.3 `openspec validate add-change-impact-analysis --strict`
