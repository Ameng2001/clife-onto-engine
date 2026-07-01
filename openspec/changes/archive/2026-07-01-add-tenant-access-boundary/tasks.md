## 1. 租户访问策略

- [x] 1.1 `authz.py`：`TenantAccessPolicy`（grant/allows/allowed_ontologies/default_allow + YAML）

## 2. 服务边界强制

- [x] 2.1 `web.py`：`create_app(..., tenant_policy=None)`；POST 读 body.tenant、GET 读 tenant 查询参数
- [x] 2.2 /ask、/plan、/explorer、/manifest、/audit 边界检查 → 403（不进引擎）；tenant_policy=None 兼容

## 3. 测试 + smoke

- [x] 3.1 `tests/test_tenant_boundary.py`：策略判定；`tests/test_web.py` 端点 403/放行/无策略兼容（fastapi 在时）
- [x] 3.2 `scripts/smoke_tenant_boundary.py`：TenantAccessPolicy 判定演示（跨租户/跨本体拒、授权通）

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图加「租户→本体访问边界（A 弧）」
- [x] 4.3 `openspec validate add-tenant-access-boundary --strict`
