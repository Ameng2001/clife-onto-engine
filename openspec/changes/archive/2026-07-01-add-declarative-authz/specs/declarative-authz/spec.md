## ADDED Requirements

### Requirement: 声明式租户可配授权策略
系统 SHALL 提供 `AuthzPolicy`：按 (ontology, action) 授予角色（`grant`），`allows(ontology, action, role)` 判定；未声明动作按 `default_allow`；支持 YAML 加载（租户配置）。策略与插件业务 guard 分离，行业无关。

#### Scenario: 授予与判定
- **WHEN** policy.grant("grass","出一地一方","施工方")
- **THEN** allows(...,"施工方")=True；allows(...,"游客")=False

#### Scenario: default-deny 未声明动作
- **WHEN** AuthzPolicy(default_allow=False) 未对某动作授权
- **THEN** 任何角色 allows(...)=False

### Requirement: 引擎前置授权门（guard 之前强制）
`ActionEngine` SHALL 接受可选 `authz`。注入时，`execute()` 在 guard **之前**判权：调用者角色无权 → 在**任何执行/暂存之前** `StructuredRejection(phase="authz")`，并审计 `decision=unauthorized`。`validate()` 同样生效。`authz=None` 时授权门不启用（向后兼容）。

#### Scenario: 未授权角色被前置拒绝且不产生副作用
- **WHEN** 注入策略只授权"施工方"，用"游客"execute 一个会写库的动作
- **THEN** 返回 phase=authz 的 StructuredRejection、无任何写入、审计留一条 unauthorized

#### Scenario: 授权角色正常执行
- **WHEN** 用被授权角色 execute 合规动作
- **THEN** 授权门放行，照常走 guard/写后规则（可 commit）

#### Scenario: 无 authz 向后兼容
- **WHEN** 不注入 authz（authz=None）
- **THEN** 授权门不启用，行为与之前一致

#### Scenario: 预演也强制授权
- **WHEN** 注入策略后对未授权角色 validate
- **THEN** ActionPreview.would_commit=False 且 violations 含 authz
