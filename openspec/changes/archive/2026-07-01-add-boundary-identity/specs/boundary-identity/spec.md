## ADDED Requirements

### Requirement: 凭据→身份解析（可插拔）
系统 SHALL 提供 `Principal(tenant, actor_id, role)` 与 `IdentityResolver.resolve(credential) → Optional[Principal]`，及一个 `StaticIdentityResolver`（api_key→Principal）。resolver 可插拔（真部署注入 JWT/OIDC）。行业无关。

#### Scenario: 合法凭据解析出身份
- **WHEN** StaticIdentityResolver 配了 key "k1"→Principal("A","u1","施工方")，resolve("k1")
- **THEN** 得到该 Principal

#### Scenario: 非法凭据解析为空
- **WHEN** resolve("bad")
- **THEN** 返回 None

### Requirement: 服务边界用认证身份而非客户声明
HTTP 服务设置 `identity_resolver` 时，各本体端点 SHALL 从 `X-Api-Key` 头取凭据解析 Principal（缺失/无效 → **401**，不进引擎），并用 **Principal.tenant** 做租户边界、**Principal.actor** 建会话。`identity_resolver=None` 时向后兼容（用声明 tenant + 后端默认 actor）。

#### Scenario: 缺/错凭据 401
- **WHEN** 设了 resolver，请求不带或带错 X-Api-Key
- **THEN** 返回 401，未触及引擎

#### Scenario: 认证身份驱动租户边界
- **WHEN** key 解析出 tenant=A，请求目标本体 A 无权访问
- **THEN** 403（用认证 tenant 判，非客户声明）

#### Scenario: 认证角色驱动 /ask 动作
- **WHEN** key 解析出 role=游客，/ask 触发一个需授权/角色的动作
- **THEN** 该动作被授权门或业务 guard 拦（用认证角色，非声明）

#### Scenario: 无 resolver 向后兼容
- **WHEN** 未设 identity_resolver
- **THEN** 端点行为与之前一致（不要求凭据）
