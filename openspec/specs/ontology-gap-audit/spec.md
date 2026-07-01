# ontology-gap-audit Specification

## Purpose
TBD - created by archiving change add-ontology-gap-audit. Update Purpose after archive.
## Requirements
### Requirement: 静态审计本体缺口（blocking / advisory 两级）
系统 SHALL 提供 `audit_gaps(registry, ontology_id) → GapReport`：静态遍历该本体定义，报 **blocking** 缺口（Action 无 handler、guard/post_rule/writes 引用悬空、Function 无 impl、Link 端点对象不存在）与 **advisory** 缺口（Rule 无 source）。审计 MUST 只读（不执行、不落库），行业无关。`GapReport.ok` = 无 blocking。

#### Scenario: 结构完整的本体无 blocking
- **WHEN** 对结构完整的 grass 审计
- **THEN** blocking 为空、ok=True；advisory 可含无 source 的 declarative guard

#### Scenario: 无 handler 的 Action 被定位
- **WHEN** 某 Action 的 impl 为 None
- **THEN** blocking 含一条 action_no_handler，subject 指向该 Action，ok=False

#### Scenario: 悬空规则引用被定位
- **WHEN** 某 Action 的 post_rule 名未在该本体注册
- **THEN** blocking 含一条 dangling_rule_ref，detail 指出缺哪条规则

#### Scenario: 悬空关系端点被定位
- **WHEN** 某 Link 的端点对象类型未声明
- **THEN** blocking 含一条 dangling_link_endpoint

### Requirement: 缺口可定位可读
`GapReport` SHALL 含 blocking/advisory 明细（kind/subject/detail）+ 计数 + summary。

#### Scenario: 报告可读
- **WHEN** 审计完成
- **THEN** 每条缺口能读出类型、具体对象名与说明

