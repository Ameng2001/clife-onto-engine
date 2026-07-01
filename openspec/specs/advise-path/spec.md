# advise-path Specification

## Purpose
TBD - created by archiving change add-advise-path. Update Purpose after archive.
## Requirements
### Requirement: 咨询路径（advise）—— 知识接地的只读领域建议
意图编译器 SHALL 支持 `kind="advise"`（`CompiledIntent.answer` 承载建议文本）：对判断/建议类问题产出基于所提供知识的领域建议。`Session.ask` SHALL 把 advise 作为一等回复 `Reply("advise", answer=...)` 返回——**只读**（不进 Action 引擎、不写库、不越权），并回写 CONTEXT 记忆。做/查/澄清/拒绝路径不变。

#### Scenario: 判断类问题得到只读建议
- **WHEN** 编译器对"重度盐碱地该先做什么"返回 kind=advise + answer（基于处置手册）
- **THEN** Session 返回 Reply(kind="advise", answer=…)，未调用 Action 引擎、未写任何对象

#### Scenario: 建议进记忆
- **WHEN** advise 回复产生
- **THEN** 该建议写入本会话 CONTEXT 记忆（供后续接地）

#### Scenario: 做/查/澄清不受影响
- **WHEN** 编译器返回 action/query/clarify
- **THEN** 各自路径与之前一致（advise 是新增第四类，不改既有）

### Requirement: advise 只读、与受治理动作分层
advise MUST NOT 触发任何写/动作/越权；真正的执行仍须走受治理 Action（guard→回滚→审计）。建议是低风险只读（理解侧），动作是受治理写（执行侧）。

#### Scenario: 建议不是动作后门
- **WHEN** advise 建议"先做工程改良"
- **THEN** 不发生任何状态改变；用户若要执行，须发起对应 Action（照常受治理兜底）

