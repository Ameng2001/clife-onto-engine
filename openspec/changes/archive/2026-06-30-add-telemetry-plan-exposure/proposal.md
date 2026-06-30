## Why

遥测 query-plan 能力（`build_plan`）已内化进内核，但目前只能在进程内调用——agent 拿不到。要让 MCP agent / HTTP 调用方能"对象 → 取它的遥测查询计划"，必须把 `build_plan` 经**两条既有传输**暴露出去（MCP 桥 + HTTP `/ask` 同服务）。这是内化遥测读"可用化"的最后一步:自有深读(语义读 OQL + 遥测读 plan)从此对 agent 完整可达。

红线不变:暴露的是**只读的产计划**(provider+plan 串,id 已代入)，引擎仍**不执行**；plan 是读工具(默认开，与 `query` 同档)，不碰治理写。

## What Changes

- `clife_onto_engine/mcp/`：`GovernedBridge` 增 `plan(object_type, key, series)` 读方法；MCP server 增 **`plan` 工具**(默认开，与 `query` 同档)，调 `build_plan`。
- `clife_onto_engine/web.py`：增 **`POST /plan`** 端点(ontology/object_type/key/series → 计划)，复用各本体 store + registry。
- 测试:`tests/test_mcp_bridge.py` 增 plan 工具 dispatch;`tests/test_web.py` 增 `/plan`(fastapi 在时);`scripts/serve_mcp.py` 的 stderr 工具清单含 plan。
- **非破坏**:纯新增读工具/端点;不改 `build_plan` 机制、不改治理写;plan 失败返回结构化 error(同 build_plan)。

## Capabilities

### New Capabilities
<!-- 无；暴露既有 telemetry-query-plan 能力。 -->

### Modified Capabilities
- `telemetry-query-plan`: 能力**经 HTTP `/plan` 与 MCP `plan` 工具暴露**给 agent/调用方(只读产计划，引擎仍不执行)。
- `umodel-governed-write-bridge`: MCP 工具面**增 `plan` 读工具**(默认开，与 `query` 同档)，让同一 agent 会话除查对象图、做受治理写外，还能取对象的遥测查询计划。

## Impact

- **改动代码**:`mcp/bridge.py`(+plan 方法、tools 列表)、`mcp/server.py`(+plan 工具 schema/dispatch)、`web.py`(+/plan)、`tests/`。
- **红线守护**:plan 只读、引擎不执行;label 防注入由 `build_plan` 既有逻辑保证;读工具默认开、写仍 opt-in(不变)。
- **拼图**:自有深读(OQL 对象图 + 遥测 plan)对 agent 完整可达——内化遥测读的可用化收口。
