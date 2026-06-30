## ADDED Requirements

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
