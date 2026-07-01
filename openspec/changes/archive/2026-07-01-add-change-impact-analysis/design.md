## Context

`replay(snapshot, registry, *, store, param_overrides) → ReplayResult`（含 replay_would_commit / violations / skipped）已就位。`OntologyVersion.registry` 是可执行 registry。变更影响 = 同一批 snapshot 对 old_registry 与 new_registry 各 replay，diff。

## Goals / Non-Goals

**Goals:** 一批历史决策，同 store/同 inputs 对旧/新版本 diff 裁决；按翻转方向归类 + 每条翻转带触发规则；隔离规则改动影响。

**Non-Goals:** 不改 replay/versioning；不做 UI（报告是结构化数据）；不做数据漂移分析（本能力刻意固定 store 以隔离规则变更）。

## Decisions

### D1. 同 store 对 old/new 各 replay，比较 would_commit（隔离规则变更）
对每个 snapshot：`ro = replay(s, old_reg, store=store)`、`rn = replay(s, new_reg, store=store)`。翻转 = `ro.replay_would_commit != rn.replay_would_commit`。**固定同一 store** → 差异只来自 registry（规则/五要素）变更，排除数据漂移。**备选**：只 replay new 对比 snapshot.decision——否，那混入了决策时与现在的数据漂移，不纯粹是规则变更影响。

### D2. 归类 + 触发规则
- newly_blocked：ro 会 commit、rn 不会 → 带 rn.violations（哪条新规则拦的）
- newly_allowed：ro 不会 commit、rn 会 commit → 带 ro.violations（原先哪条拦、现在放开）
- unchanged / skipped（任一侧 skip 则该条 skipped）
`ImpactReport`：计数 + `flips`（每条：ontology/action/direction/triggering_rules/decision_ref）。

### D3. 复用 replay 的只读与边界
change_impact 不新增执行路径，全走 replay→validate（无副作用）。function-backed 规则读传入 store 的边界继承自 replay（D5 of 砖2）。

## Risks / Trade-offs

- [old/new 某侧 validate_supported=False] → 该条 skipped（继承 replay 的结构化 skip）。
- [store 选择影响 function-backed 结果] → 文档讲清：固定 store 隔离规则变更；要评估"新规则 + 当前数据"就传当前 store。
- [大批量性能] → 每条两次 validate（无副作用、内存）；量大可外部分批，本期不做并行。

## Open Questions

- 是否支持"对同一 new 版本、对比 recorded decision"的第二模式（含数据漂移）？倾向本期只做隔离模式（D1）；含漂移模式留小扩展（把 old_registry 传 None 即用 snapshot.decision 作基线）。
