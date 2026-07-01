## Context

`build_plan(registry, store, object_type, key, series, *, namespace)` 当前:查绑定→读对象实例→把 `binding.labels` 的对象字段值代入模板 `$占位`→返回计划。模板方言由作者写(provider 无关)。metric/prometheus 已通。log/ES 的两个新需求:① ES DSL 是 JSON 模板(字符串代入照样работает,白名单已排除 `"{}` 故 JSON 不破);② log 要运行时过滤(level/时间窗),非对象字段。

## Goals / Non-Goals

**Goals:** ES/log 方言跑在同一 build_plan(零机制改);运行时 params 解析对象字段之外的占位;同防注入;未解析占位即拒。

**Non-Goals:** 不连 ES、不执行;不做 SQL(留扩展点,但机制已支持——加绑定即可);不做时间窗语义解析(`$since` 由调用方给值,引擎只代入)。

## Decisions

### D1. 两段占位解析:对象 label 先,运行时 params 后
`build_plan` 先按 `binding.labels` 从实例代入(原逻辑不变);再扫描模板**剩余** `$占位`,从 `params` 解析。label 与 params 同名时 label 优先(已被实例代入)。**备选**:合并成一个映射——否,对象字段(治理数据)与运行时入参(调用方给)来源不同,分两段更清晰、且 label 仍受"缺字段即拒"约束。

### D2. 运行时 params 同白名单防注入
params 的值同样过 `_SAFE_LABEL` 校验,越界即拒——log 的 level/时间窗也是注入面,纪律一致。**备选**:只校验 label——否,运行时入参更是不可信来源,必须校验。

### D3. 未解析占位 → 结构化拒绝
两段代入后若模板仍含 `$占位`(既非 label 又未在 params 给),返回 error(列出缺哪个),**不产残缺计划**。这是正确性改进,对既有 metric 绑定无影响(它们占位全是 label)。**备选**:残留占位放行——否,会产出打不了后端的废计划。

### D4. ES DSL 模板用 JSON 字符串,值代入安全
ES 绑定的 `template` 是一段 ES DSL 的 JSON 字符串(含 `$parcel`/`$level`/`$since`)。白名单排除 `"`/`{`/`}` 保证代入值不破 JSON 结构。`build_plan` 不解析 JSON、不校验 DSL 合法性(方言由作者负责),只安全代入——保持机制 provider 无关。

## Risks / Trace-offs

- [代入值破坏 JSON 结构] → 白名单已禁 `"{}` 等;值只能是安全标量。
- [params 透传到暴露层但被滥用] → 暴露层只搬运给 build_plan,防注入仍在 build_plan;params 可选,缺省 {}。
- [触及 build_plan 签名] → 新增可选 kw `params=None`,既有调用零改;暴露层显式传 params。

## Open Questions

- 时间窗占位(`$since`)是否需引擎提供"相对时间"语义糖(如 now-1h)？倾向否——引擎只代入字面值,相对时间由调用方/skill 解析，保持"只产计划不解释方言"。
- SQL 方言要不要本期顺带加一个绑定证明三 provider？倾向不——ES 已证 provider 无关,SQL 同骨架随时加,避免本期膨胀。
