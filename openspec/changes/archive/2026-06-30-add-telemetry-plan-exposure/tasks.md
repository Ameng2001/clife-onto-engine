## 1. MCP 暴露

- [x] 1.1 `mcp/bridge.py`：`GovernedBridge.plan(object_type, key, series)` → `build_plan(..., namespace=ontology_id)`；`tools()` 加 `plan`（默认开）
- [x] 1.2 `mcp/server.py`：`plan` 工具 schema（object_type/key/series）+ dispatch case

## 2. HTTP 暴露

- [x] 2.1 `web.py`：`POST /plan {ontology, object_type, key, series}` → backends[ontology].store → build_plan；未知本体 404

## 3. 测试

- [x] 3.1 `tests/test_mcp_bridge.py`：plan 工具 tools/list 默认含 plan；tools/call plan → 含已代入 id 的 PromQL
- [x] 3.2 `tests/test_web.py`：`POST /plan` 正例（含 id 代入）+ 缺字段/注入透传 error（fastapi 在时）
- [x] 3.3 回归：全量 pytest + smoke 全绿

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；docs/04 §9 第一块砖注记补"已经 HTTP/MCP 暴露"
- [x] 4.2 `openspec validate add-telemetry-plan-exposure --strict`
