## Why

路线图 B(治理深化）+ C（建模闭环）的**共享地基**是两件事：**本体版本化** 与 **决策重放**。它俩一旦就位，就同时解锁：规则变更影响分析（B2）、Action dry-run 规模化（B3）、CQ 验收回路（C3）。

好消息是接口早已留好、这是**闭环不是新起**：
- `AuditSnapshot` 已存 `inputs_snapshot`（动作参数）+ `actor_id/role` + `rules_evaluated` + `schema_version` —— **重放的原料齐了**。
- `ActionEngine.validate()` → `ActionPreview`（无副作用、从注入的 registry 解析）—— **重放执行器已半成品**。
- `schema_version` 已贯穿 execute→audit，但只是**字符串标签**，背后没有物化的版本。

本变更把 `schema_version` 从标签变成**可寻址的不可变版本**，并加**决策重放**（用存的 inputs 只读重跑 validate，支持反事实 param 覆盖）。

## What Changes

- 新增 `clife_onto_engine/versioning.py`：`snapshot_ontology(registry, ontology_id, version) → OntologyVersion`（把某本体的五要素定义 + 映射冻结成不可变版本）；`OntologyVersionStore`（按 (ontology_id, version) 持有多个版本、put/get/list）。版本的 registry 具备 `get_action/get_rule/get_function`，可直接喂给 `ActionEngine`。
- 新增 `clife_onto_engine/replay.py`：`replay(snapshot, registry, *, store=None, param_overrides=None) → ReplayResult` —— 从 `AuditSnapshot` 重建 actor+params（可 param_overrides 做反事实），对给定 registry（活的或某版本）跑 `validate()`，返回 `{original_decision, replay_would_commit, flipped, violations, counterfactual, ...}`。
- 测试 + smoke：grass 决策重放复现裁决；反事实（换非乡土草种 → flipped=True）；对版本快照重放（换规则版本 → 裁决变）；版本不可变（快照后改活 registry 不影响旧版本）。
- **非破坏**：纯新增模块；不改 `validate()`/`execute()`/`AuditSnapshot`；行业无关。

## Capabilities

### New Capabilities
- `ontology-versioning`: 把某本体在某时刻的五要素定义 + 映射**快照成不可变、可寻址的版本**（`schema_version` 物化）；版本可被 `ActionEngine` 直接解析执行。多版本共存、互不影响。
- `decision-replay`: 用 `AuditSnapshot` 存的 inputs 对指定 registry（活的或某版本）**只读重放** `validate`，复现/对比裁决；支持 param 覆盖做**反事实**。是 B2 变更影响分析、C3 CQ 验收的共享原语。

### Modified Capabilities
<!-- 不改既有 capability 需求；本变更是其上的治理生命周期地基。 -->

## Impact

- **新增代码**：`clife_onto_engine/versioning.py`、`clife_onto_engine/replay.py`、`scripts/smoke_replay.py`、`tests/test_versioning_replay.py`。
- **红线守护**：行业无关（内核纯净 CI）；重放**只读**（复用 validate 的无副作用，永不落库）；版本**不可变**（冻结快照）。
- **范围诚实**：重放的 function-backed 规则读**调用方提供的 store**（默认空 → declarative-only 可复现；function-backed 需传相关 store）。**点位历史 store 快照**（完全忠实的时点重放）留后续扩展。
- **解锁**：砖3 规则变更影响分析（批量重放跨版本 diff）、砖4 CQ 验收（一组治理问题对版本重放）都建在这两块上。
