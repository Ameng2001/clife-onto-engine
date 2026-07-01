# capability-violation-audit Specification

## Purpose
TBD - created by archiving change add-capability-violation-audit. Update Purpose after archive.
## Requirements
### Requirement: Capability 越界→回滚+审计+结构化拒绝（不崩）
当 Action handler 触发 Capability 沙箱拦截（`CapabilityError`：stage 未声明类型/跨租户/内核直达等），`ActionEngine.execute()` SHALL **确定性回滚**（丢弃暂存、无残留写）、审计一条 `decision=capability_violation`（留痕越界详情）、返回 `StructuredRejection(phase="capability")`——而非抛异常崩溃。`validate()` 同样捕获，返回 `ActionPreview(would_commit=False)` 含 capability 违规。合法（不越界）动作行为不变。

#### Scenario: 越界 handler 被审计并结构化拒绝
- **WHEN** 某 Action 的 handler 试图 stage 一个未在 writes 声明的对象类型
- **THEN** execute 返回 phase=capability 的 StructuredRejection、无任何写入、审计留一条 capability_violation

#### Scenario: 预演也捕获越界
- **WHEN** 对越界 handler 的动作 validate
- **THEN** ActionPreview.would_commit=False 且 violations 含 capability

#### Scenario: 合法动作不受影响
- **WHEN** handler 只操作已声明能力
- **THEN** 照常执行（可 commit），无 capability 违规

