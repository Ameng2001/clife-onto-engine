## Why

A 弧安全硬化：**Capability 越界运行时审计**。Capability 沙箱四层约束（租户/类型作用域、写声明强制、Function 最小权限、能力收窄）已能拦住越界，但拦法是**抛 CapabilityError**——在生产/不完全可信插件下，越界会让请求**崩溃**，且**没有留痕**（谁试图突破隔离、试了什么，查不到）。

改成生产化处置：引擎捕获 CapabilityError → **确定性回滚**（无残留写）+ **安全审计留痕**（decision=capability_violation）+ **结构化拒绝**（phase=capability），而非崩溃。把安全边界从"崩"变"可观测 + 兜底"。

## What Changes

- `ActionEngine`：`execute()` 与 `validate()` 把 handler 调用（`spec.impl(cap)`）包在 try/except `CapabilityError`：
  - execute：回滚 overlay + 审计 `capability_violation` + 返回 `StructuredRejection(phase="capability")`。
  - validate：回滚 + 返回 `ActionPreview(would_commit=False, violations=[capability])`。
  - 新增 `_capability_violation(msg)` 构造统一 Violation。
- 测试 + smoke：越界 handler（stage 未声明类型）→ 不崩、无写、审计留 `capability_violation`、结构化拒绝；正常 handler 不受影响。
- **非破坏**：合法动作行为不变（不越界即无感）；不改沙箱四层约束本身；行业无关。

## Capabilities

### New Capabilities
- `capability-violation-audit`: Action handler 越界（沙箱拦截）时，引擎确定性回滚 + 安全审计留痕（capability_violation）+ 结构化拒绝，而非崩溃。让隔离突破尝试可观测、可追溯，且不产生副作用。

## Impact

- **改动代码**：`clife_onto_engine/kernel/action_engine.py`（handler try/except + _capability_violation）、`scripts/smoke_capability_audit.py`、`tests/test_capability_audit.py`。
- **红线守护**：越界即回滚（无残留写）+ 审计（安全可观测）+ 结构化拒绝（不崩）；沙箱四层约束不变（拦得住的仍拦住）；行业无关（内核纯净 CI）。
- **承接 A 弧**：认证/隔离/授权之上再加"隔离突破可观测"。后续：NebulaGraph space 生命周期、引擎自身可观测。
