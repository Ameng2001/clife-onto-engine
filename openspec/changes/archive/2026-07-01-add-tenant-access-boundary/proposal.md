## Why

A 弧第二块砖：**租户→本体访问边界**。授权门（上一块）管"谁能做什么"，但还没管"**哪个租户能碰哪个本体**"。当前 HTTP/MCP 服务同时托管多本体（grass/chili…），任何调用者都能命中任一 `/{ontology}` 端点——多租户下这是越界。

把隔离从 Capability 内（已有：本 ontology 内作用域）延伸到**服务边界**：调用者租户只能访问被授权的本体，跨租户请求在**入口就 403**，不进引擎。策略租户可配、默认不启用即向后兼容。

## What Changes

- `clife_onto_engine/authz.py` 增 `TenantAccessPolicy`：tenant_id → 允许的 ontology 集合；`allows(tenant, ontology)`；`default_allow`；YAML 加载。
- `web.py`：`create_app(..., tenant_policy=None)`；POST 端点（/ask、/plan）读 `tenant` 字段、GET 端点（/explorer、/manifest、/audit）读 `tenant` 查询参数；tenant_policy 设了且不允许 → **403**（不进引擎）。默认 `tenant_policy=None` → 不启用（向后兼容）。
- 测试 + smoke：策略只授权 tenantA→grass；tenantA 访问 grass 通、访问 chili 403；tenantB 访问 grass 403；无策略照常。
- **非破坏**：纯新增（policy + web 可选参数 + 请求可选 tenant）；不改引擎/五要素；行业无关。

## Capabilities

### New Capabilities
- `tenant-access-boundary`: 服务边界的租户→本体访问控制。调用者租户无权访问某本体时，请求在入口 403（不进引擎）。策略租户可配、默认不启用兼容。把多租户隔离从 Capability 内延伸到服务边界。

## Impact

- **改动代码**：`authz.py`（+TenantAccessPolicy）、`web.py`（+tenant_policy 与各端点边界检查）、`scripts/smoke_tenant_boundary.py`、`tests/test_tenant_boundary.py`（+test_web.py 端点）。
- **红线守护**：跨租户请求入口即拒（不触引擎/数据）；默认不启用向后兼容；行业无关；与 Capability 内作用域互补（边界 + 内隔离双层）。
- **承接 A 弧**：授权门（谁能做）+ 租户边界（哪租户碰哪本体）。后续：HTTP 身份解析（凭据→tenant/actor）、Capability 越界运行时审计、space 生命周期。
