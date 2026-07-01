## 1. 身份解析

- [x] 1.1 `clife_onto_engine/identity.py`：`Principal`、`IdentityResolver`(Protocol)、`StaticIdentityResolver`(api_key→Principal)

## 2. web 边界身份

- [x] 2.1 `web.py`：`create_app(..., identity_resolver=None)`；`_principal(x_api_key)` → Principal 或 401
- [x] 2.2 各端点用 Principal.tenant 走 _check_tenant、`/ask` 用 Principal.actor 建会话（session 键含 actor_id）
- [x] 2.3 identity_resolver=None 向后兼容（声明 tenant + 后端 actor）

## 3. 测试 + smoke

- [x] 3.1 `tests/test_identity.py`：StaticIdentityResolver 解析/None
- [x] 3.2 `tests/test_web.py`：缺/错 key 401；认证 tenant 驱动边界；认证 role 驱动 /ask；无 resolver 兼容
- [x] 3.3 `scripts/smoke_identity.py`：合法 key→Principal→租户边界+授权门用认证身份；非法→401

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图加「服务边界身份解析（A 弧闭环访问控制）」
- [x] 4.3 `openspec validate add-boundary-identity --strict`
