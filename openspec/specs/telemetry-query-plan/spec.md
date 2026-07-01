# telemetry-query-plan Specification

## Purpose
TBD - created by archiving change add-telemetry-query-plan. Update Purpose after archive.
## Requirements
### Requirement: 声明对象到可观测后端的遥测绑定
系统 SHALL 在映射层支持**遥测绑定**:声明一个对象类型到可观测后端(provider ∈ prometheus/elasticsearch/sql)的 labels 映射与若干 series（metric/log，每个含名称与生成器模板）。绑定 MUST 行业无关、声明式（YAML 可加载），与 `ObjectMapping` 同层。

#### Scenario: 加载遥测绑定
- **WHEN** 插件声明 `Site` 的遥测绑定（provider=prometheus，labels: parcel_id→parcel，series: 一个 PromQL 模板）
- **THEN** 映射注册表持有该绑定，可按 (namespace, object_type) 解析

### Requirement: 据对象实例生成可执行查询计划（不执行）
系统 SHALL 提供 `build_plan(registry, store, object_type, key, series_name)`：查绑定、读对象实例的 label 字段值、安全代入生成器模板，返回 `{provider, plan, resolved_labels}`。引擎 MUST NOT 连接或执行后端——只产计划串。

#### Scenario: 生成 PromQL 计划
- **WHEN** 对实例 `Site/parcel_001`（parcel_id=parcel_001）调用 build_plan 取某 metric
- **THEN** 返回的 plan 是把 `parcel_001` 代入模板后的可执行 PromQL，provider=prometheus，resolved_labels 含 parcel=parcel_001；全程无网络

#### Scenario: 缺 label 字段被结构化拒绝
- **WHEN** 对象实例缺少绑定所需的某 label 字段
- **THEN** 返回结构化错误指出缺哪个 label，不产出残缺计划

### Requirement: 代入防注入
系统 SHALL 在代入前校验 label 值不含查询/模板元字符；越界即拒（与 OQL「引擎校验、不裸拼」同纪律）。

#### Scenario: 注入式 label 值被拦
- **WHEN** 某对象 label 字段值含 PromQL/DSL 元字符（如 `"} or up{`）
- **THEN** build_plan 拒绝并报错，不产出计划

### Requirement: 行业无关 · provider 无关
遥测机制 MUST 不含任何行业词汇（内核纯净 CI 通过）；新增 provider（es/sql）MUST 只需新增绑定（模板按该 provider 方言），不改 `build_plan` 机制。

#### Scenario: 内核纯净
- **WHEN** 运行 `check_kernel_purity.py`
- **THEN** `query/telemetry.py` 与 `sdk/mapping.py` 的遥测绑定无行业词汇，检查通过

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

### Requirement: 支持 log/Elasticsearch 方言（provider 无关）
`telemetry-query-plan` SHALL 支持 metric 之外的方言：声明 provider=elasticsearch、kind=log、模板为 ES DSL 的遥测序列，由**同一** `build_plan` 生成可执行计划。加新方言 MUST 只需新增绑定（模板按该 provider 方言写），不改 `build_plan` 机制。

#### Scenario: 生成 ES log 计划
- **WHEN** 对绑定了 ES log 序列的对象实例调用 build_plan
- **THEN** 返回 `{ok:true, provider:"elasticsearch", kind:"log", plan:<已代入 id 的 ES DSL>}`；引擎未连 ES、未执行

#### Scenario: 同一 build_plan 跑多方言
- **WHEN** 对同一对象分别取 prometheus metric 与 elasticsearch log 序列
- **THEN** 两者都由同一 build_plan 正确生成（provider/kind 各自正确），机制无分支于行业

### Requirement: 运行时过滤参数
`build_plan` SHALL 接受可选运行时 `params`：对象 label 代入后，模板中**剩余**的 `$占位` 由 `params` 解析（典型用于 log 的 level/时间窗/limit）。运行时参数值 MUST 同样经白名单防注入校验。两段代入后仍有未解析占位 MUST 结构化拒绝（不产残缺计划）。

#### Scenario: 运行时参数代入
- **WHEN** ES log 模板含 `$parcel`（对象）+ `$level`/`$since`（运行时），调用方传 params={level:ERROR, since:"now-1h"}
- **THEN** 计划把对象 id 与运行时值都代入，无残留 `$占位`

#### Scenario: 运行时参数注入被拦
- **WHEN** params 某值含查询/模板元字符（如 `"} or `）
- **THEN** build_plan 拒绝并报防注入错误，不产计划

#### Scenario: 未解析占位被拒
- **WHEN** 模板含一个既非对象 label 又未在 params 给出的 `$占位`
- **THEN** 返回结构化错误指出缺哪个占位，不产残缺计划

#### Scenario: 既有 metric 绑定不受影响
- **WHEN** 不传 params 调用一个占位全为对象 label 的 metric 序列
- **THEN** 行为与之前一致（params 默认空，向后兼容）

