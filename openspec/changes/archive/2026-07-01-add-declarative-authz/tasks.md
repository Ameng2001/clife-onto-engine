## 1. 授权策略

- [x] 1.1 `clife_onto_engine/authz.py`：`AuthzPolicy`（grant/allows/granted_roles/default_allow）+ YAML 加载

## 2. 引擎前置授权门

- [x] 2.1 `ActionEngine` 加可选 `authz` 参数 + `_authz_violation`
- [x] 2.2 `execute()` guard 之前判权 → StructuredRejection(phase=authz) + 审计 unauthorized（任何写之前）
- [x] 2.3 `validate()` 同样授权门；authz=None 向后兼容

## 3. 测试 + smoke

- [x] 3.1 `tests/test_authz.py`：授予/判定/default-deny；未授权 execute→unauthorized 无写+审计；授权→正常；validate 授权门；无 authz 兼容；YAML
- [x] 3.2 `scripts/smoke_authz.py`：grass 注入策略——游客越权→unauthorized（无写、审计留痕）；施工方→commit

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图加「声明式授权（生产化·多租户 A 弧起步）」
- [x] 4.3 `openspec validate add-declarative-authz --strict`
