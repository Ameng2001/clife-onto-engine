## ADDED Requirements

### Requirement: 租户→本体访问策略
系统 SHALL 提供 `TenantAccessPolicy`：按 tenant_id 授予可访问的 ontology（`grant`），`allows(tenant, ontology)` 判定；未声明按 `default_allow`；支持 YAML。行业无关。

#### Scenario: 授予与判定
- **WHEN** policy.grant("tenantA","grass")
- **THEN** allows("tenantA","grass")=True；allows("tenantA","chili")=False（default-deny）；allows("tenantB","grass")=False

### Requirement: 服务边界强制租户→本体访问
HTTP 服务 SHALL 在设置 `tenant_policy` 时，于各本体端点（/ask、/plan、/explorer、/manifest、/audit）校验调用者租户对目标本体的访问权：无权 → **403**，请求**不进引擎**。`tenant_policy=None` 时不启用（向后兼容）。

#### Scenario: 跨本体访问被拒
- **WHEN** 策略只授权 tenantA→grass，tenantA 请求 /ask?tenant... 目标 chili
- **THEN** 返回 403，未触及引擎

#### Scenario: 授权本体正常
- **WHEN** tenantA 请求目标 grass
- **THEN** 边界放行，照常处理

#### Scenario: 无策略向后兼容
- **WHEN** 未设 tenant_policy
- **THEN** 各端点行为与之前一致（不校验租户）
