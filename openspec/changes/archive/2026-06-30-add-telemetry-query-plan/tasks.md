## 1. 映射层：遥测绑定

- [x] 1.1 `sdk/mapping.py`：`TelemetryBinding`(object_type, namespace, provider, labels: dict, series: tuple[{name, template}])；`MappingRegistry` 加 `telemetry` 表 + add/get
- [x] 1.2 YAML 加载：`load_yaml` 支持 `telemetry:` 段（provider/labels/series）

## 2. 计划生成（引擎只产计划、不执行）

- [x] 2.1 `query/telemetry.py` `build_plan(registry, store, object_type, key, series_name)`：查绑定→读实例 label 值→安全代入模板→`{provider, plan, resolved_labels}`
- [x] 2.2 防注入：label 值校验（无查询/模板元字符），越界结构化拒绝
- [x] 2.3 缺 label 字段 → 结构化错误（指出缺哪个）
- [x] 2.4 成本计量：plan 生成计 1 个 telemetry-plan 算子（沿用 CostMeter 思路）

## 3. grass demo + 验证

- [x] 3.1 grass `Site` 声明一个 prometheus 遥测绑定（PromQL 模板，parcel_id→label）
- [x] 3.2 `scripts/smoke_telemetry.py`：build_plan 对 parcel_001 → 断言 id 代入正确、provider 对、无网络；注入式值被拦
- [x] 3.3 `tests/test_telemetry_plan.py`：正例 + 缺字段 + 防注入 + 行业无关，锁进 CI

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + 新 smoke 全绿
- [x] 4.2 docs/04 §9：把「遥测/query-plan」从路线图标注为「已落第一块砖（metric/prometheus）」，log/es 留扩展点
- [x] 4.3 `openspec validate add-telemetry-query-plan --strict`
