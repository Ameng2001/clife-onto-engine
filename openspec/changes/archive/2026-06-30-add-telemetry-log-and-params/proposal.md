## Why

遥测 query-plan 第一块砖只打通了 metric/prometheus。要兑现"provider 无关、加方言只加绑定"的设计承诺，需真正铺一个**不同方言**(log/Elasticsearch DSL)，证明 `build_plan` 机制零改。

同时暴露一个真实缺口:**log 查询离不开运行时过滤**(level、时间窗、limit)，这些**不是对象字段**，当前 `build_plan` 只从对象实例代入 label，无法表达。故需给 `build_plan` 加**运行时参数**(同防注入纪律)——没有它，log 绑定只是玩具。

这两件事合起来才算"铺通 log/ES 方言":ES DSL 模板 + 运行时过滤参数，跑在**同一个** `build_plan` 上。

## What Changes

- `query/telemetry.py`：`build_plan(..., params: dict | None = None)` —— 对象 label 先代入,剩余 `$占位` 从运行时 `params` 解析(同白名单防注入);仍有未解析占位 → 结构化拒绝(不产残缺计划)。
- grass `Field`/`Site` 增一个 **elasticsearch / log 绑定**(ES DSL JSON 模板,含对象 label + 运行时 `$level`/`$since`)。
- 暴露层透传 `params`：MCP `plan` 工具与 HTTP `/plan` 增可选 `params`。
- 测试 + smoke:ES log 计划(对象 id + 运行时 level/since 代入、provider=elasticsearch、kind=log);运行时参数注入被拦;未解析占位拒绝;**同一 build_plan 同时跑 prometheus 与 elasticsearch**。
- **非破坏**:`params` 默认 None → 既有 metric 绑定零感知;机制不变,只加"剩余占位从 params 解析"一步。

## Capabilities

### New Capabilities
<!-- 无；扩展既有 telemetry-query-plan。 -->

### Modified Capabilities
- `telemetry-query-plan`: 支持 **log/Elasticsearch 方言**(provider=elasticsearch、kind=log、ES DSL 模板)与**运行时过滤参数**(`params`，对象字段之外的占位由调用方传入，同防注入)。证明 provider 无关——加方言只加绑定，机制零改。

## Impact

- **改动代码**:`query/telemetry.py`(+params 解析)、`mcp/bridge.py` + `mcp/server.py`(plan 工具透传 params)、`web.py`(/plan 透传 params)、grass 绑定 yaml、`scripts/smoke_telemetry.py` + `tests/test_telemetry_plan.py`。
- **红线守护**:运行时 params 同样白名单防注入;未解析占位即拒(不产残缺计划);引擎仍只产计划不执行;provider 无关(ES 只是新绑定)。
- **拼图**:遥测读从单方言(metric)走向多方言(metric+log),坐实"内化的深读 provider 无关"。
