## ADDED Requirements

### Requirement: 声明式 CQ 套件对本体版本跑验收
系统 SHALL 提供 `run_cq_suite(cqs, registry, *, store=None) → CQReport`：对给定 registry（活的或某 `OntologyVersion.registry`）逐条跑 competency question——`ActionCQ` 走 `validate`（无副作用）判裁决期望，`QueryCQ` 走 `oql_execute` 判行数期望——产出 pass/fail 报告。执行 MUST 只读。内核 MUST NOT 含任何具体 CQ（套件由插件/建模端提供）。

#### Scenario: 动作期望裁决通过
- **WHEN** ActionCQ 期望"合规草种 出一地一方 → commit"，对含该规则的版本 + 相关 store 跑
- **THEN** 该 CQ passed=True

#### Scenario: 动作期望被指定规则拦
- **WHEN** ActionCQ 期望"非乡土草种 → reject·乡土合规"
- **THEN** would_commit=False 且 violations 含"乡土合规" 时 passed=True；否则 failed 并注明期望 vs 实际

#### Scenario: 查询期望行数
- **WHEN** QueryCQ 期望某 OQL 至少返回 1 行，对相关 store 跑
- **THEN** 行数≥门槛则 passed=True

### Requirement: 版本化验收抓能力回归
同一 CQ 套件对不同本体版本运行时，SHALL 反映该版本能力——某版本缺失/削弱了某规则时，依赖它的 CQ MUST fail。

#### Scenario: 缺规则版本被 CQ 抓住
- **WHEN** 对"故意去掉乡土合规的版本"跑"非乡土草种该被乡土合规拦"的 CQ
- **THEN** 该 CQ failed（能力回归被验收门抓住）

### Requirement: 报告结构
`CQReport` SHALL 含 total/passed/failed 计数与每条结果（名称/类型/passed/期望/实际/detail）与 summary。

#### Scenario: 报告可读
- **WHEN** 套件跑完
- **THEN** 报告给出通过/失败计数，且每条失败能读出期望 vs 实际
