## ADDED Requirements

### Requirement: MCP 桥暴露 plan 读工具
`GovernedBridge` SHALL 暴露一个 `plan` 读工具（默认开，与 `query` 同档，不受 `enable_act` 门控），调 `build_plan` 返回对象的遥测查询计划。plan MUST 是只读、产计划不执行；不影响写工具 `act` 的 opt-in 规则。

#### Scenario: plan 工具默认可见
- **WHEN** 构造 `GovernedBridge`（无论 enable_act 与否）并 `tools/list`
- **THEN** 工具清单含 `plan`（与 `query` 一样默认开）；`act` 仍仅在 enable_act 时出现

#### Scenario: 经 plan 工具取计划
- **WHEN** `tools/call` name=plan arguments={object_type:Site, key:parcel_001, series:soil_moisture}
- **THEN** 返回 build_plan 结构化结果（含已代入 id 的 PromQL）；不发生任何写、不执行计划
