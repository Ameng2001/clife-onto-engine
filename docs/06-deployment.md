# 06 · 部署 Runbook

把数智本体引擎跑成一个**可访问的服务**：一句口语 `POST /ask` →（做/查/咨询/澄清），前置**认证 → 租户边界 → 授权门**，数据经**声明式租户接入**按 schema 校验落库。本篇是从零到「一个真实用户能打一次」的可复现路径。

> 目标读者：把实例部起来的人。代码定位/设计见 [`README`](../README.md) 与 [`docs/01–05`](.)。

---

## 1. 部署了什么

```
                       ┌──────── serve.py（FastAPI）────────┐
   X-Api-Key ──▶ 认证(identity) ─▶ 租户边界(tenant_policy) ─▶ 每本体后端
                  401 无效           403 跨租户/跨本体          │
                                                              ├─ ActionEngine(+authz 授权门) ─▶ guard→回滚→审计
                                                              ├─ store（memory | NebulaGraph）
                                                              └─ compiler（真 Qwen，惰性）
   数据来源：ONTO_TENANTS ─▶ load_tenant（按本体 schema 校验落库）│ 未声明则 demo seed
```

四层访问控制（纵深防御，各层独立可开关）：

| 层 | 组件 | 拦什么 | 失败 |
|---|---|---|---|
| 认证 | `identity.yaml` → IdentityResolver | 凭据无效/缺失 | **401** |
| 租户边界 | `tenant_policy.yaml` → TenantAccessPolicy | 租户访问无权的本体 | **403**（不进引擎） |
| 授权门 | `authz.<ont>.yaml` → AuthzPolicy | 角色无权执行某动作 | **phase=authz 拒 + 审计 unauthorized** |
| 能力沙箱 | Capability（内建） | 动作越界写/跨租户 | 回滚 + capability_violation 审计 |

**全部可选**：不设对应 env 即不启用该层（向后兼容，便于本地裸跑）。

---

## 2. 前置

- Python 3.10+；`pip install -r requirements-server.txt`（FastAPI/uvicorn）。
- LLM 凭据：`llm.local.json`（gitignore）或 env（`DASHSCOPE_API_KEY` 等）。**无 LLM 也能起服务**，只是 `/ask` 首次编译会失败——冒烟可先只测访问控制层（401/403 在编译前）。
- 可选真图库：Docker（NebulaGraph，见 §4.3）。

---

## 3. 配置

样例全在 [`deploy/`](../deploy/)（**示例密钥，勿用于生产**）：

| 文件 | 作用 |
|---|---|
| `deploy/.env.example` | 环境变量样例（复制为 `deploy/.env`） |
| `deploy/authz.grass.yaml` / `authz.chili.yaml` | 每本体授权门：动作 → 允许角色 |
| `deploy/tenant_policy.yaml` | 租户 → 可访问本体 |
| `deploy/identity.yaml` | api_key → Principal（tenant/actor/role） |
| `tenants/mengcao/tenant.yaml` + `data/*.csv` | 租户数据源（声明式接入，见 [`docs/05`](05-e2e-validation.md) 测试/§租户接入） |

关键 env（全 `deploy/.env.example` 有）：

```bash
ONTO_BACKEND=memory                                    # memory | nebula
ONTO_ONTOLOGIES=grass
ONTO_TENANTS=grass=tenants/mengcao/tenant.yaml         # 声明式数据（不设则 demo seed）
ONTO_AUTHZ=grass=deploy/authz.grass.yaml               # 授权门
ONTO_TENANT_POLICY=deploy/tenant_policy.yaml           # 租户边界
ONTO_IDENTITY=deploy/identity.yaml                     # 认证
```

**接真业务数据**：把 `tenants/mengcao/data/*.csv` 换成真实导出（同表头），或指向 DB 导出文件。脏行会在启动日志按 `IngestReport` 逐条留因（缺主键/必填/类型/未声明对象），不静默丢、不崩。

---

## 4. 启动

### 4.1 本地（memory 后端，最快）

```bash
set -a; . deploy/.env; set +a          # 载入配置（或手动 export）
python scripts/serve.py 0.0.0.0 8000   # /docs 看接口
```
启动日志应见：
```
[grass] 租户数据接入：载入 33 · 拒绝 0
[authz] grass ← deploy/authz.grass.yaml
[tenant-policy] ← deploy/tenant_policy.yaml
[identity] ← deploy/identity.yaml（5 凭据）
```

### 4.2 Docker（单容器，memory 后端）

```bash
docker build -t clife-onto-engine .
docker run --rm -p 8000:8000 \
  --env-file deploy/.env \
  -e DASHSCOPE_API_KEY=sk-xxx \
  -v "$PWD/tenants:/app/tenants:ro" -v "$PWD/deploy:/app/deploy:ro" \
  clife-onto-engine
```
密钥**运行时 env 注入**、不进镜像（见 `README` §容器化）。

### 4.3 docker-compose（NebulaGraph 真图库后端）

```bash
docker compose up -d          # 起 NebulaGraph + serve（ONTO_BACKEND=nebula）
```
serve 会等 graphd 起来、bootstrap 建库建模再灌数（见 `docker-compose.yml` 与 `deploy/nebula/`）。

---

## 5. 冒烟（验证四层 + 回路）

启用 identity 后（实测值）：

```bash
curl -s localhost:8000/health
# {"status":"ok","ontologies":["grass"]}

# 无凭据 → 401（认证层，编译前拦）
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/ask \
  -H 'Content-Type: application/json' -d '{"ontology":"grass","utterance":"巴彦淖尔有哪些地块"}'
# 401

# mengcao 施工方 → 200（读回路通）
curl -s -X POST localhost:8000/ask -H 'X-Api-Key: mc-builder-001' \
  -H 'Content-Type: application/json' -d '{"ontology":"grass","utterance":"巴彦淖尔有哪些地块"}'
# {"kind":"query","rows":[...]}

# chili 租户访问 grass → 403（租户边界）
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/ask \
  -H 'X-Api-Key: chili-grower-1' -H 'Content-Type: application/json' \
  -d '{"ontology":"grass","utterance":"x"}'
# 403

# 游客写动作 → phase=authz 拒（授权门；游客不在 出一地一方 授权角色）
curl -s -X POST localhost:8000/ask -H 'X-Api-Key: mc-guest-0001' \
  -H 'Content-Type: application/json' \
  -d '{"ontology":"grass","utterance":"给 parcel_001 出方案用碱茅预算300"}'
# {"kind":"rejected","violations":[{"rule":"authz",...}]}
```

> 401 / 200 / 403 三态已在 TestClient 端到端实测通过（app 装配 33 对象租户数据 + 5 凭据 + 授权门 + 租户边界）。

---

## 6. 延迟 / 成本

**引擎管道延迟**（`python scripts/bench.py`，离线脚本编译器，隔离 LLM）——实测：

| 类别 | p50 | p95 | p99 |
|---|---|---|---|
| 读·查询 | ~0.13ms | ~0.23ms | ~0.27ms |
| 写·提交 | ~0.14ms | ~0.26ms | ~0.49ms |
| 写·拒绝 | ~0.12ms | ~0.23ms | ~0.27ms |

**结论**：治理管道（记忆接地→路由→guard/规则/回滚/审计）开销**亚毫秒**，可忽略。**端到端延迟由 LLM 主导**。

**真 Qwen 延迟/成本**：由模型与网络决定（通常几百 ms~数秒/请求）。量法——直接对 `/ask` 计时：
```bash
curl -s -o /dev/null -w 'total=%{time_total}s\n' -X POST localhost:8000/ask \
  -H 'X-Api-Key: mc-builder-001' -H 'Content-Type: application/json' \
  -d '{"ontology":"grass","utterance":"给 parcel_001 出一地一方用碱茅预算300"}'
```
token 成本看 DashScope 控制台用量。容量规划：并发上限≈LLM 端点并发；引擎本身不是瓶颈。

---

## 7. 安全注意

- `deploy/*.yaml` 里是**示例密钥**，**勿用于生产**。生产密钥走密钥管理（env/Secret），不入库。
- 生产换 `StaticIdentityResolver` 为 JWT/OIDC 实现（同 `IdentityResolver` 协议，`web.py` 不变）。
- 认证身份**由服务端解析**（`X-Api-Key`），租户边界/授权门/动作角色**一律用认证出的身份**，不信客户端声明的 tenant。
- 默认 `default_allow: false`（收紧）：未声明的动作/租户默认拒。

---

## 8. 下一步（诚实边界）

- 本 runbook 用 **mock 租户数据**（`tenants/mengcao/data/*.csv`，形如真实导出）。接真业务导出即产品化下一步。
- 真实用户观察、真 Qwen 延迟/成本实测、并发压测：需要一个真部署环境 + 真实用户，本篇提供到「能起、能打、四层可验」为止。
