## Why

生产化·多租户第一块砖：**声明式授权**。要上真客户，运行时必须能回答"**谁能做什么**"——当前 HTTP 层 actor 是每本体硬编码，任何调用者都以固定角色执行，没有授权。补一个**引擎前置授权门**：调用者角色无权执行某动作，就在**任何执行/暂存之前**结构化拒绝并审计（decision=unauthorized）。

授权策略**租户可配**（注入不同 `AuthzPolicy`），与插件的业务 guard 分离：插件声明"这动作需要什么"，租户配置"谁被授权"。这是多租户"隔离 + 授权"从占位变强制的第一步。

## What Changes

- 新增 `clife_onto_engine/authz.py`：`AuthzPolicy`——(ontology, action) → 允许角色集合；`grant/allows/granted_roles`；YAML 加载（租户配置）；`default_allow`（可 default-deny）。
- `ActionEngine` 增可选 `authz` 参数 + 前置授权门：`execute()` 在 guard **之前**判权，无权 → `StructuredRejection(phase="authz")` + 审计 `decision=unauthorized`；`validate()` 同样生效（dry-run/replay/CQ 若注入 authz 则一致）。
- 默认 `authz=None` → 授权门不启用（**向后兼容**，既有 99 测试不受影响）。
- 测试 + smoke：注入策略后，未授权角色执行 → unauthorized（无任何写、审计留痕）；授权角色 → 正常走 guard/规则；default-deny 未声明动作被拒；YAML 加载。
- **非破坏**：纯新增（引擎加可选参数）；不改五要素/规则/回滚；行业无关（内核纯净 CI）。

## Capabilities

### New Capabilities
- `declarative-authz`: 声明式、租户可配的动作授权策略 + 引擎前置强制。调用者角色无权执行某动作时，在 guard/执行之前结构化拒绝（unauthorized）并审计。与插件业务 guard 分离（插件声明需求、租户配置授权），是生产化多租户的授权地基。

## Impact

- **改动代码**：`clife_onto_engine/authz.py`（新）、`clife_onto_engine/kernel/action_engine.py`（+authz 参数与授权门）、`scripts/smoke_authz.py`、`tests/test_authz.py`。
- **红线守护**：授权在**任何写/暂存之前**（不留副作用）；unauthorized 结构化拒绝 + 审计（合规留痕"谁越权试了什么"）；默认不启用向后兼容；行业无关。
- **承接 A 弧**：这是"谁能做什么"。后续 A 砖：租户→本体访问边界（服务层）、Capability 租户作用域运行时强制审计、space 生命周期。
