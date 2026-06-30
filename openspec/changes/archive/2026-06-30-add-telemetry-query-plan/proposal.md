## Why

目标是对标 Palantir 的本体语义 OS——**语义面全自有**。语义读(OQL 查受治理对象图/关系)已自有;但**遥测读**(对象绑定 metric/log 后端、生成可执行查询计划)目前借 UModel。要把它**内化**进内核,本体 OS 才能不依赖外部就"把读做深"(对象 → 它的指标/日志,一步可达)。

这是 [docs/04 §9](../../../docs/04-umodel-interop.md) 内化路线的**第一块砖**,也是 UModel 从"读层"降为"互操作"的前提:我们自己能生成遥测查询计划后,UModel 只剩 import-export 互通的角色。

严守红线:**行业无关机制层**(与映射注册表同层),**不是** `plugins/ops` 业务域;引擎**只产查询计划、不当 TSDB**(给出 PromQL/ES DSL,不连后端执行——与 UModel 同立场)。

## What Changes

- 映射层(`sdk/mapping.py`)增**遥测绑定** `TelemetryBinding`(声明式 YAML):对象 → 可观测后端(prometheus/es/sql)的 labels 映射 + metric/log 的**生成器模板**(含 `$label` 占位)。
- 新增 `clife_onto_engine/query/telemetry.py`:`build_plan(registry, store, object_type, key, metric_or_query)` —— 查绑定、把对象实例的 label 值代入模板 → 返回**可执行计划**(后端 + 计划串,id 已代入),**不执行**。
- 算子级成本计量(沿用 OQL CostMeter 思路,plan 生成计 1 个 telemetry-plan 算子)。
- grass demo 绑定 + 离线 smoke/test:`Site` 绑定一个 PromQL 指标,断言生成的计划把 `parcel_id` 正确代入、provider 正确、引擎不触网。
- **非破坏**:纯新增机制;不改五要素核心/OQL/Action 引擎;行业无关(内核纯净 CI);不写后端、不引重依赖。

## Capabilities

### New Capabilities
- `telemetry-query-plan`: 行业无关的内核能力——声明对象到可观测后端(metric/log)的绑定,据对象实例**生成可执行查询计划**(PromQL/ES DSL/SQL,id 已代入),引擎只产计划不执行。与 OQL(对象图读)互补,构成本体 OS 自有的"深读"。

### Modified Capabilities
<!-- 无；与 umodel-* 既有 capability 互补，不改其需求。 -->

## Impact

- **新增/改动代码**:`sdk/mapping.py`(+TelemetryBinding 声明与 YAML 加载)、`query/telemetry.py`(plan 生成)、grass demo 绑定 + `scripts/smoke_telemetry.py` + `tests/test_telemetry_plan.py`。
- **设计参考**:vendored `third-party/umodel-schemas/` 的 `metric_set`/`data_link`/`storage`(已在仓库),内化采同构思路。
- **红线守护**:行业无关(内核纯净 CI);引擎不连后端(只产计划);provider 无关(模板驱动);声明式 YAML(配置即 PR)。
- **战略意义**:内化遥测读后,UModel 降为 interop/import-export(docs/04 §9)。语义读(OQL)+ 遥测读(本能力)+ 治理写(Action)+ 审计/HIL = 自有完整语义面。
