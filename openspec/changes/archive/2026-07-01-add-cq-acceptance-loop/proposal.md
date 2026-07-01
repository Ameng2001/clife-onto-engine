## Why

砖1/2/3 已把"本体可版本化、决策可重放、变更可评估"做出来。**闭合建模端的最后一环是 CQ 验收（C3）**：声明一组 **competency questions**（本体能力验证问题）——动作的期望裁决（该 commit / 该被某规则拦）、查询的期望结果——对**某个本体版本**跑 pass/fail。

这让建模→运行时成**闭环**：建模端（astra-studio）改本体产出新版本 → 对新版本跑 CQ 套件 → pass/fail 回喂建模端。CQ 也是变更影响分析的"黄金期望集"——版本演进时重跑 CQ 即知能力有没有回归。

## What Changes

- 新增 `clife_onto_engine/cq.py`：
  - `ActionCQ(name, ontology, action, params, actor_role, expect, expect_rule=None)`——expect ∈ {commit, reject}；expect_rule 可选（该被哪条规则拦）。
  - `QueryCQ(name, ontology, oql, min_rows=1)`——期望查询至少返回 N 行。
  - `run_cq_suite(cqs, registry, *, store=None) → CQReport`——对给定 registry（活的或某版本）逐条跑：动作走 `validate`（无副作用）、查询走 `oql_execute`；判 pass/fail。
- `CQReport`：total/passed/failed + 每条结果（期望 vs 实际 + 触发规则/行数）+ summary。
- 测试 + smoke：grass CQ 套件（"合规草种该 commit"、"非乡土草种该被乡土合规拦"、"越权角色该被拦"、"某查询该有行"）对当前版本全 pass；对"故意去掉乡土合规的版本"→ 相应 CQ fail（能力回归被抓）。
- **非破坏**：纯新增；复用 validate/oql_execute（只读、无副作用）；行业无关。

## Capabilities

### New Capabilities
- `cq-acceptance-loop`: 声明式 competency question 套件（动作期望裁决 + 查询期望结果），对某本体版本跑 pass/fail，产出验收报告。闭合建模→运行时环，并作版本演进的能力回归门。

## Impact

- **新增代码**：`clife_onto_engine/cq.py`、`scripts/smoke_cq.py`、`tests/test_cq.py`。
- **红线守护**：只读（validate/oql_execute 无副作用）；行业无关（内核纯净 CI）；CQ 声明本身与本体分离（套件由插件/建模端提供，内核只跑）。
- **完成 B+C 弧**：砖1 版本化 + 砖2 重放 + 砖3 变更影响（B2）+ 砖4 CQ 验收（C3）= "活的本体·治理化变更生命周期"闭环。C1（TODO(FDE) 回填）作独立后置 track。
