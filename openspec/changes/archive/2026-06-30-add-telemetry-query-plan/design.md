## Context

引擎已有:语义读 `query/oql.py`(JSON-AST OQL 查对象图)、映射注册表 `sdk/mapping.py`(对象→物理表/列,槽位2)。缺的是**遥测读**:对象→可观测后端(metric/log)+ 生成查询计划。UModel 的做法(已 vendored 在 `third-party/umodel-schemas/`):`metric_set`(label keys + metric generator,如 `sum(rate(...{id="$id"}[1m]))`) + `data_link`(对象字段→label) + `storage`(后端),`get_metrics` 返回**查询计划**而非数据。内化采同构思路,但落进我们既有的声明式映射层。

## Goals / Non-Goals

**Goals:**
- 声明对象→可观测后端的遥测绑定(provider 无关:prometheus/es/sql)。
- 据对象**实例**生成可执行查询计划(模板 + 实例 label 值代入),引擎**不执行**。
- 行业无关机制层;与 OQL 互补,构成自有"深读"。

**Non-Goals:**
- 不连后端、不执行计划、不当 TSDB(只产计划串,调用方拿去打 Prometheus/ES)。
- 不做 `plugins/ops` 业务域;不内化 UModel 的 RCA skill(那是交互层的事)。
- 本期不做 ES/SQL 完整渲染,先打通 prometheus 模板 + 机制骨架(ES/SQL 留扩展点)。

## Decisions

### D1. 遥测绑定落映射层(`sdk/mapping.py`),与 ObjectMapping 同层
遥测是"对象→外部数据源"的另一种映射,天然属槽位2。`TelemetryBinding(object_type, namespace, kind, provider, labels, series)`,声明式 YAML 加载(同 `objects.yaml`)。**备选**:新增元模型第六要素——否,遥测是映射/绑定,不是新本体语义;塞进五要素会破"内核只懂五要素"的契约。

### D2. 生成器模板 + 实例 label 代入,provider 无关
`series` 每项含 `name` + `template`(如 PromQL `sum(rate(x{parcel="$parcel_id"}[1m]))`);`labels` 把对象字段映射到模板占位。`build_plan` 读对象实例(经 store)、取 label 字段值、字符串安全代入 → `{provider, plan, resolved_labels}`。**备选**:每 provider 写专用渲染器——后续可加,但 v1 用统一模板代入最薄;provider 只决定 plan 的方言由模板作者负责。

### D3. 引擎只产计划、不执行(与 UModel 同立场)
`build_plan` 返回计划串 + provider + 代入的 label,**不**发网络。调用方(skill/agent/HTTP)拿计划自行打后端。保持引擎"产计划不当 TSDB",也天然离线可测。**备选**:引擎直连 Prometheus——否,引入网络/依赖/后端耦合,破"薄适配"且不可离线测。

### D4. 安全代入:label 值白名单校验,防注入
代入前校验 label 值(对象字段实际值)不含模板/查询元字符(防 PromQL/DSL 注入),越界即拒——与 OQL "LLM 不写查询串、引擎校验" 同纪律。**备选**:裸字符串拼接——否,注入风险。

### D5. 成本计量沿用 OQL CostMeter 思路
plan 生成计 1 个 `telemetry-plan` 算子,纳入既有成本/计费口径。

## Risks / Trade-offs

- [模板方言绑死 provider] → `provider` 字段显式声明;模板由绑定作者按 provider 写;`build_plan` 只代入不解释方言 → 加 ES/SQL 只是加绑定,不改机制。
- [label 注入] → D4 白名单校验。
- [对象实例缺 label 字段] → 缺字段即结构化错误(指出缺哪个 label),不产残缺计划。
- [触及映射层] → 纯新增 `TelemetryBinding`,不改 ObjectMapping/LinkMapping;既有映射测试不受影响。

## Migration Plan

纯新增:映射层加绑定类型 + `query/telemetry.py` + grass demo 绑定。回滚 = 移除。无数据迁移;不声明遥测绑定的本体零感知。

## Open Questions

- log 计划(ES DSL/SLS)v1 是否覆盖,还是先只 metric(prometheus)打通骨架?(倾向先 metric,log 同骨架后续加)
- 派生遥测视图(跨对象聚合的指标)是否需要,还是先单对象绑定?(倾向先单对象,聚合留后)
- 是否同时给 HTTP 面加 `/plan` 端点暴露 build_plan?(倾向本期只做内核能力 + smoke,HTTP/MCP 暴露另起)
