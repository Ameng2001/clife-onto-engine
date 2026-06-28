# 本地 NebulaGraph（dev）

供本地验证 `clife-onto-engine` 的 `NebulaGraphStore` adapter。单实例，非生产拓扑。

## 启动

```bash
docker compose -f deploy/nebula/docker-compose.yml up -d
pip install nebula3-python
```

graphd 暴露在宿主 `127.0.0.1:9669`（默认账号 `root` / 任意密码，dev 用 `nebula`）。

## 注册存储节点（首次必做）

NebulaGraph v3 启动后需把 storaged 注册进集群，否则 `CREATE SPACE` 无可用存储。
`NebulaGraphStore.bootstrap()` 已**自动**执行 `ADD HOSTS "storaged0":9779` 并轮询
`SHOW HOSTS` 等待 ONLINE，无需手动操作。手动等价命令（如需）：

```sql
ADD HOSTS "storaged0":9779;
SHOW HOSTS;        -- 等 storaged0 Status = ONLINE
```

## 验证

```bash
python scripts/nebula_integration.py     # bootstrap + 写读 + Search Around + OQL
```

预期：`get_object` / `search_around` 正反向均返回，OQL 多跳与聚合结果与内存后端一致。

## 隔离模型

一个 `ontology_id` ↔ 一个 NebulaGraph **space**（grass→space `grass`）。
Object 类型 → TAG，Link 类型 → EDGE，业务主键 → VID。跨 space 默认零可见 = 多本体/租户硬隔离。

## 停止 / 清理

```bash
docker compose -f deploy/nebula/docker-compose.yml down        # 停止
docker compose -f deploy/nebula/docker-compose.yml down -v     # 停止并删数据卷
```
