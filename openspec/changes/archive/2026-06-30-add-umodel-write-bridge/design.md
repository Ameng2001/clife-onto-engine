## Context

Phase 1 让 UModel 成为引擎之上的只读层(导出器 + sidecar + 在线验收跑通)。引擎的受治理写在 `ActionEngine.execute`(guard→stage_write→写后规则→提交/确定性回滚→审计快照),门面是 `Session.ask`(NL 路由 做/查/澄清)与 `web.py` 的 `/ask`。`ActionResult.written` = tuple of `(object_type, key)`;`decision ∈ {committed, pending_hil}`,被拒时返回 `violations`。

phase 2 要让 MCP agent 在 UModel 同台既读又做,但**写不能走 UModel**(UModel `entity_write` 会绕过治理)。

## Goals / Non-Goals

**Goals:**
- 引擎 MCP server,暴露受治理 `query`(读)+ opt-in `act`(写)工具。
- `act` 全程经 `ActionEngine`;提交成功后把**已提交**状态反映进 UModel 读层 workspace。
- 红线可测:合法但违规的动作被引擎确定性拒绝且**不反映**;拒绝/HIL 不落读层。

**Non-Goals:**
- 不启用 UModel 自身 `entity_write`/`entity_expire`(写旁路永远 disabled)。
- 不改五要素/Action 引擎/回滚/审计。
- 不把治理逻辑搬进 MCP 层——MCP 只是门面,裁决在引擎。
- 不做 UModel→引擎的反向写(UModel 永远只读)。

## Decisions

### D1. MCP server 落 `clife_onto_engine/mcp/`,与 `web.py` 同层(门面,非内核)
复用 `Session`/`ActionEngine`,像 `web.py` 一样组装。行业无关(内核纯净 CI 透明)。**备选**:塞进 `web.py`——否,MCP 是独立传输,单独模块清晰。

### D2. 写工具 `act` 用**结构化**入参,不用 NL
`act(ontology, action, params, actor_role)` 直达 `ActionEngine.execute`,绕开意图编译的不确定性——MCP agent 已能选结构化工具。NL 写仍可经 `query`/`ask` 路径。**备选**:`act` 收 NL 再编译——否,写路径要确定性,结构化更稳。

### D3. 写工具默认 **opt-in**(沿用 UModel "读默认开/写需授权"范式)
server 启动需显式开关(如 `--enable-act`/环境变量)才注册 `act`;默认只读。映射引擎 HIL/治理纪律。

### D4. 提交后反映:只反映 `committed`,从引擎 store 读真值
`act` 拿到 `ActionResult` 后:`committed` → 对每个 `(type,key)` 用 `store.get_object` 读已提交数据 → 复用导出器 `_eid`/payload 成形 → UModel REST `entities:write`(关系同理)。`pending_hil`/`rejected` → **不反映**,原样返回结构化结果。**备选**:反映 staged(未提交)状态——否,违反"只读层只接已提交"红线。

### D5. 反映失败不回滚引擎提交(读层最终一致)
引擎提交是权威;反映 UModel 是读层同步,失败只记日志/告警,不影响已提交的治理写(引擎不依赖读层)。下次导出/反映补齐。**备选**:反映失败即回滚——否,会让权威写依赖读层可用性,违反解耦红线。

### D6. MCP 传输用成熟件
官方 `mcp` Python SDK(stdio/HTTP)或最小 JSON-RPC stdio 薄实现二选一;反映用 stdlib `urllib`。不自研协议、不引重依赖(开源优先·薄适配)。

## Risks / Trade-offs

- [agent 误以为 UModel 能直接写] → server 永不启用 UModel `entity_write`;`act` 是唯一写入口且经引擎;文档红线 + smoke 断言。
- [反映与引擎状态漂移] → 反映只取已提交真值(D4);失败可由 `export_umodel.py` 全量重导补齐;读层本就最终一致。
- [`act` 暴露未声明动作] → `ActionEngine` 只认 registry 已注册 Action,未注册即 `ResolutionError`,与 `/ask` 同一兜底。
- [HIL 动作被反映] → 只反映 `decision==committed`;`pending_hil` 显式排除并测试覆盖。
- [写工具默认开导致越权] → D3 默认 opt-in;actor_role 经引擎 guard(如"角色权限")校验。

## Migration Plan

纯增量:加 `clife_onto_engine/mcp/` + 两个脚本 + 文档。回滚 = 移除模块,引擎/web/phase 1 不受影响。无数据迁移。

## Open Questions

- MCP 传输优先选官方 `mcp` SDK 还是最小 JSON-RPC stdio?(倾向先最小 stdio 跑通语义,再评估 SDK——更薄、零新依赖)
- 反映关系:`act` 的 `written` 只含对象写;关系若由 Action 经 `stage_link` 产生,需 `ActionResult` 暴露 staged links 才能反映(本期若动作不写关系则跳过,留 TODO)。
- `query` 工具是否复用 phase 1 的 UModel SPL(读经 UModel)还是经引擎 OQL?(倾向经引擎 OQL,保持"受治理读"一致;UModel SPL 作为浏览面并存)
