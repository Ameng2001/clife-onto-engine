## 1. MCP server 骨架（门面，与 web.py 同层）

- [x] 1.1 建 `clife_onto_engine/mcp/__init__.py` + `server.py`:最小 JSON-RPC stdio 循环（initialize/tools.list/tools.call），行业无关
- [x] 1.2 组装方式复用 `web.py`：注入 registry/store/compiler/actor，持有 `Session`/`ActionEngine`
- [x] 1.3 写开关:默认只读;`--enable-act` / 环境变量开启才注册 `act`

## 2. 读工具 query（受治理读，非 UModel SPL 旁路）

- [x] 2.1 `query` 工具:NL→OQL 或结构化 OQL，经引擎 `oql_execute`（受 schema 校验/防注入）
- [x] 2.2 返回结构化行 + 成本计量

## 3. 写工具 act（经 Action 引擎，本体兜底）

- [x] 3.1 `act(ontology, action, params, actor_role)` → `ActionEngine.execute`，返回结构化 committed/rejected/pending_hil
- [x] 3.2 未声明动作 → 结构化解析错误（与 /ask 同兜底）
- [x] 3.3 拒绝返回 `violations`（结构化，非异常），供 agent 自动重试

## 4. 提交后反映（只反映已提交，复用 phase 1 成形）

- [x] 4.1 反映 adapter：committed 时对每个 written (type,key) `store.get_object` 读真值 → 复用 `umodel._eid`/payload → UModel REST `entities:write`
- [x] 4.2 关系反映：若 Action 产生 stage_link，需 `ActionResult` 暴露 staged links 才反映；本期动作不写关系则记 TODO 跳过
- [x] 4.3 `pending_hil`/`rejected` 显式不反映；反映失败仅记录、不回滚引擎提交

## 5. 红线守护 · smoke

- [x] 5.1 `scripts/smoke_mcp_bridge.py`：离线断言——合法违规动作被引擎 rejected 且读层零写入；HIL 动作 pending 不反映
- [x] 5.2 断言 UModel `entity_write`/`entity_expire` 在桥配置中保持 disabled（无写旁路）
- [x] 5.3 断言读层缺席时 `act` 照常提交（反映失败不回滚）

## 6. 在线端到端（真实 UModel）

- [x] 6.1 `scripts/verify_mcp_bridge_online.sh`：起 sidecar → MCP `act` 出一地一方(合规草种) → commit → `.entity` 在读层查到新 Project/SeedPack
- [x] 6.2 反例：`act` 用非乡土草种 → rejected → 读层无变化（本体兜底的活证据）

## 7. 文档 · 收尾

- [x] 7.1 `docs/04-umodel-interop.md` 补「写桥」节：架构图 + 红线（UModel 无写旁路 / 写只经引擎 / 读层只反映已提交）
- [x] 7.2 `tests/test_mcp_bridge.py`：act 提交/拒绝/HIL 不反映 + 无写旁路，锁进 CI
- [x] 7.3 全量 `pytest` + 新 smoke 全绿；`check_kernel_purity.py` 对 `mcp/` 通过
- [x] 7.4 `openspec validate add-umodel-write-bridge --strict`；准备归档
