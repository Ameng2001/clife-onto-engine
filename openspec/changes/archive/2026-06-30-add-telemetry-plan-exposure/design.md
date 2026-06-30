## Context

`query/telemetry.py:build_plan(registry, store, object_type, key, series, *, namespace)` 已实现并归档（capability `telemetry-query-plan`）：据对象实例生成可执行计划，引擎不执行。现需经两条既有传输暴露：MCP 桥（`mcp/`，per-ontology 的 `GovernedBridge`）与 HTTP（`web.py` 的 `create_app`，per-ontology backends 持 store）。

## Goals / Non-Goals

**Goals:** MCP `plan` 工具 + HTTP `/plan` 暴露 `build_plan`；plan 是读工具（默认开）；失败结构化。

**Non-Goals:** 不改 `build_plan` 机制；不执行计划；不引新依赖；不动治理写 opt-in 规则。

## Decisions

### D1. `plan` 是读工具，默认开（与 `query` 同档，非 `act` 的 opt-in）
plan 只产只读计划、不写，故与 `query` 同列入 `bridge.tools()`，不受 `enable_act` 门控。**备选**:跟 `act` 一起 opt-in——否，读不该被写开关挡。

### D2. 桥 plan 方法签名跟随 bridge 的 per-ontology 语境
`bridge.plan(object_type, key, series)` → `build_plan(registry, store, object_type, key, series, namespace=self.ontology_id)`，直接转 build_plan 的结构化结果（含 ok/error）。

### D3. HTTP `/plan` 复用 backends 的 store
`POST /plan {ontology, object_type, key, series}` → 取 `backends[ontology].store` → build_plan，404 未知本体（与 `/manifest` 同兜底）。

### D4. 透传 build_plan 的结构化结果（不在传输层加治理语义）
两条传输都只是搬运：build_plan 的 `{ok, provider, plan, resolved_labels, cost}` 或 `{ok:False, error}` 原样返回。防注入/缺字段裁决都在 build_plan，传输层不重复。

## Risks / Trade-offs

- [agent 误以为 plan 会执行] → 工具描述明确"只产计划、不执行，调用方自行打后端"；返回无 result/value 字段。
- [触及 web.py 端点] → 纯新增 `/plan`；现有 `/ask` 等不变；fastapi 缺席时 web 测试照常跳过。

## Open Questions

- `/plan` 与 MCP plan 是否需批量（一次多 series）？倾向单 series，批量留后续。
