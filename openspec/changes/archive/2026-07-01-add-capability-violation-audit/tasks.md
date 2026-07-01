## 1. 引擎捕获越界

- [x] 1.1 `action_engine.py`：`_capability_violation(msg)` 构造统一 Violation
- [x] 1.2 `execute()`：handler try/except CapabilityError → 回滚 overlay + 审计 capability_violation + StructuredRejection(phase=capability)
- [x] 1.3 `validate()`：handler try/except → 回滚 + ActionPreview(would_commit=False, capability 违规)

## 2. 测试 + smoke

- [x] 2.1 `tests/test_capability_audit.py`：越界 handler→不崩/无写/审计 capability_violation/phase=capability；validate 捕获；合法动作不受影响
- [x] 2.2 `scripts/smoke_capability_audit.py`：注册越界测试动作，execute→结构化拒绝+审计留痕

## 3. 收尾

- [x] 3.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 3.2 README §16 路线图加「Capability 越界运行时审计（A 弧·安全可观测）」
- [x] 3.3 `openspec validate add-capability-violation-audit --strict`
