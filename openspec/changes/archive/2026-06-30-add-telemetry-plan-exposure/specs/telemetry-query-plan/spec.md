## ADDED Requirements

### Requirement: 遥测计划经 HTTP 与 MCP 暴露给调用方
`telemetry-query-plan` 能力 SHALL 经 HTTP `POST /plan` 与 MCP `plan` 工具暴露：调用方给 (ontology, object_type, key, series) 即取得 `build_plan` 的结构化结果。两条传输 MUST 只搬运 `build_plan` 的结果（成功含 provider/plan/resolved_labels/cost；失败含 error），引擎仍**不执行**计划。

#### Scenario: HTTP 取计划
- **WHEN** `POST /plan {"ontology":"grass","object_type":"Site","key":"parcel_001","series":"soil_moisture"}`
- **THEN** 返回 `{ok:true, provider:"prometheus", plan:"...parcel=\"parcel_001\"..."}`；引擎未触网、未执行

#### Scenario: MCP 取计划
- **WHEN** MCP `tools/call` name=plan arguments={object_type:Site, key:parcel_001, series:soil_moisture}
- **THEN** content 文本是 build_plan 的结构化结果（含已代入 id 的 PromQL）

#### Scenario: 透传结构化错误
- **WHEN** 经任一传输请求一个缺 label 字段或注入式值的实例
- **THEN** 返回 `{ok:false, error:...}`（与 build_plan 一致），传输层不另加语义
