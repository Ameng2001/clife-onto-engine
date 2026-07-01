## Why

A 弧第三块砖：**服务边界身份解析**。授权门（谁能做）+ 租户边界（哪租户碰哪本体）已就位，但它们用的 tenant/actor 还是**客户端声明**的——任何调用者自称 tenantA/施工方即被信任。生产化必须把身份从"声明"换成"**认证**"：调用者出示凭据 → 服务解析成 `Principal(tenant, actor, role)` → 授权门/租户边界用**认证身份**判定。凭据无效 → 401。

这把前两块砖闭环：认证出的 tenant 喂租户边界、认证出的 role 喂授权门。

## What Changes

- 新增 `clife_onto_engine/identity.py`：`Principal(tenant, actor_id, role)`；`IdentityResolver` 协议 `resolve(credential) → Optional[Principal]`；`StaticIdentityResolver`（api_key→Principal 字典，简单部署/测试用；真部署注入 JWT/OIDC）。
- `web.py`：`create_app(..., identity_resolver=None)`。设了则各端点从 `X-Api-Key` 头取凭据 → 解析 Principal（无效/缺失 → **401**）；用 **Principal.tenant** 走租户边界、**Principal.actor** 建会话（`/ask` 的动作用认证角色）。`identity_resolver=None` → 向后兼容（用声明 tenant + 后端默认 actor）。
- 测试 + smoke：合法 key → 解析出 Principal、其 tenant/role 生效；非法/缺 key → 401；`/ask` 用认证角色（越权角色被授权门/业务 guard 拦）；无 resolver 兼容。
- **非破坏**：纯新增（web 可选参数 + 请求头）；不改引擎/五要素；行业无关。

## Capabilities

### New Capabilities
- `boundary-identity`: 服务边界的凭据→身份解析（可插拔 IdentityResolver）。请求凭据解析成 Principal(tenant/actor/role)，无效 401；授权门与租户边界改用**认证身份**而非客户声明，闭环生产化访问控制。

## Impact

- **改动代码**：`identity.py`（新）、`web.py`（+identity_resolver、凭据解析、Principal 驱动 tenant/actor）、`scripts/smoke_identity.py`、`tests/test_identity.py` + `test_web.py`。
- **红线守护**：无 resolver 向后兼容；凭据无效即 401（不进引擎）；resolver 可插拔（内核不绑死认证方案）；行业无关。
- **闭合 A 前两块**：认证身份 → 租户边界 + 授权门。后续：Capability 越界运行时审计、NebulaGraph space 生命周期。
