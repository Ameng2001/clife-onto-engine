## Why

砖1（本体版本化）+ 砖2（决策重放）已就位。B2 **规则变更影响分析**直接建在它俩上：把一批历史决策的 inputs 同时对**旧版本**与**新版本**各重放一次（同一 store、只换 registry），diff 裁决——精确回答治理侧最想问的：**"这条规则一改，过去哪些 committed 会翻成 rejected（新拦），哪些 rejected 会翻成 committed（新放）？"**

同 store、同 inputs、只换 registry —— 从而**隔离出"规则改动"本身的影响**（排除数据漂移），这是"变更可评估"从口号变可测的关键。

## What Changes

- 新增 `clife_onto_engine/change_impact.py`：`change_impact(snapshots, old_registry, new_registry, *, store=None) → ImpactReport` —— 每个快照对 old/new 各 `replay` 一次（同 store），按翻转方向归类。
- `ImpactReport`：total / unchanged / newly_blocked（旧 commit→新 reject）/ newly_allowed（旧 reject→新 commit）/ skipped；每条翻转带**触发规则**（新版命中的 violations）与决策标识。
- 测试 + smoke：一批 grass 历史决策，对"预算≥500 更严版本"做影响分析 → 精确列出被新拦的决策 + 触发规则「预算非负」；对更宽版本 → newly_allowed。
- **非破坏**：纯新增；复用 `replay`（只读，永不落库）；行业无关。

## Capabilities

### New Capabilities
- `change-impact-analysis`: 对一批历史决策，同 inputs/同 store 分别对旧/新本体版本重放并 diff，产出**变更影响报告**（新拦/新放/不变/跳过 + 每条翻转的触发规则）。隔离规则改动本身的影响，供上线前评估。

## Impact

- **新增代码**：`clife_onto_engine/change_impact.py`、`scripts/smoke_change_impact.py`、`tests/test_change_impact.py`。
- **红线守护**：只读（复用 replay/validate 无副作用）；行业无关（内核纯净 CI）；边界继承 replay（function-backed 读调用方 store）。
- **解锁 + 承接**：这是 B2；与砖4（CQ 验收，C3）并列建在版本化+重放上。合起来兑现"活的本体·治理化变更生命周期"。
