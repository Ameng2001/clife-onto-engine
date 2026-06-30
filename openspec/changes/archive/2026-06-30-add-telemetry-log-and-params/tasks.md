## 1. build_plan 运行时参数

- [x] 1.1 `query/telemetry.py`：`build_plan(..., params=None)`——对象 label 先代入；扫描剩余 `$占位` 从 params 解析（同 `_SAFE_LABEL` 防注入）
- [x] 1.2 两段代入后仍有未解析 `$占位` → 结构化拒绝（指出缺哪个）
- [x] 1.3 既有 metric 路径不受影响（params 默认空）

## 2. grass ES/log 绑定

- [x] 2.1 grass `mappings/objects.yaml`：给 `Site` 加一个 provider=elasticsearch、kind=log 序列（ES DSL JSON 模板，含 `$parcel` + `$level` + `$since`）

## 3. 暴露层透传 params

- [x] 3.1 `mcp/bridge.py` `plan(object_type,key,series,params=None)` + server `plan` 工具 schema 加可选 params
- [x] 3.2 `web.py` `/plan` body 加可选 params，透传 build_plan

## 4. 测试 + smoke

- [x] 4.1 `tests/test_telemetry_plan.py`：ES log 计划（provider/kind 正确、id+运行时代入）；运行时注入被拦；未解析占位拒绝；同一 build_plan 跑 prom+es
- [x] 4.2 `scripts/smoke_telemetry.py`：补 ES log 一例
- [x] 4.3 `tests/test_mcp_bridge.py` / `test_web.py`：plan 透传 params 取 ES log 计划

## 5. 收尾

- [x] 5.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 5.2 docs/04 §9：第一块砖注记更新为「metric/prometheus + log/elasticsearch，运行时过滤参数」
- [x] 5.3 `openspec validate add-telemetry-log-and-params --strict`
