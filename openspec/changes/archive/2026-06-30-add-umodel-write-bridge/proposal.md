## Why

Phase 1（[add-umodel-interop](../archive/2026-06-30-add-umodel-interop/)）让 UModel 成为引擎之上的**只读**层:对象图能被浏览、被 MCP agent 读。但一个 MCP agent 在 UModel 里只能**看**,不能**做**——任何受治理的写仍要离开 UModel、另走引擎 `/ask`。

把两半区合体:让 agent 在同一个 MCP 会话里**既读对象图、又触发受治理的写**(guard→写后规则→确定性回滚→审计),写完读层即刻反映新状态。这才是完整的 OAG demo——**理解与行动同台,且行动被本体兜底**。

关键纪律(延续 phase 1 红线):**绝不开 UModel 自己的 `entity_write` 写旁路**(那会绕过治理)。写**只**经引擎 Action 引擎;UModel 只接收**已提交、已校验**的结果用于读层同步。治理永远在模型之外。

## What Changes

- 新增**引擎 MCP server**(Python 薄适配,行业无关)`clife_onto_engine/mcp/`:暴露
  - 读工具 `query`(NL→OQL 或结构化 OQL,经引擎受治理读,**非** UModel SPL 旁路);
  - **opt-in 写工具** `act`(ontology, action, params, actor_role):执行一个**已声明**的 Action,全程走 `ActionEngine`(guard→写后规则→提交/回滚→审计快照),返回结构化结果(committed/rejected+violations/pending_hil)。
- 新增**提交后反映**:`act` 提交成功后,把 `ActionResult.written`(已提交 (type,key))从引擎 store 读出、经 UModel REST `entities:write`/`relations:write` 写进读层 workspace——复用 phase 1 导出器的 `_eid`/payload 成形。`pending_hil`/`rejected` **不反映**(HIL 关口/拒绝即不落读层)。
- 新增 `scripts/smoke_mcp_bridge.py`:离线断言 `act` 经引擎兜底(合法动作违反规则照样 rejected、不反映);`scripts/verify_mcp_bridge_online.sh`:真实 UModel 下端到端(act→commit→读层可见)。
- 文档:`docs/04-umodel-interop.md` 补「写桥」节(架构图 + 红线:UModel 无写旁路、写只经引擎、读层只反映已提交)。
- **非破坏**:不改内核五要素/Action 引擎;MCP server 是新增门面(与 `web.py` 同层调 `Session`/`ActionEngine`);内核纯净 CI 不受影响;UModel 仍以 sidecar 形态、读半区只读。

## Capabilities

### New Capabilities
- `umodel-governed-write-bridge`: 一个引擎 MCP server,暴露受治理读工具与 opt-in 写工具 `act`;`act` 全程经 Action 引擎(guard/写后规则/回滚/审计),提交成功后把**已提交**状态反映进 UModel 读层;拒绝/HIL 不反映。UModel 不获得任何写旁路。

### Modified Capabilities
<!-- 不改 phase 1 的 umodel-pack-export / umodel-read-layer 的既有需求;本变更是其上的新增写通道。 -->

## Impact

- **新增代码**:`clife_onto_engine/mcp/`(server + 工具定义 + 提交后反映 adapter)、`scripts/smoke_mcp_bridge.py`、`scripts/verify_mcp_bridge_online.sh`。
- **依赖**:MCP 传输用成熟件(官方 `mcp` Python SDK 或最小 JSON-RPC stdio 薄实现);反映用 stdlib `urllib`/`json`,不新增重依赖。
- **红线守护**:① 写只经 `ActionEngine`,UModel `entity_write` 保持 disabled(无写旁路);② 读层只接收已提交、已审计的状态;③ MCP server 行业无关(内核纯净 CI);④ 引擎不依赖 UModel——读层缺席时 `act` 照常提交,只是不反映。
- **承接 phase 1**:复用导出器 `_eid`/payload 成形与 `verify_umodel_online.sh` 的装载范式。
