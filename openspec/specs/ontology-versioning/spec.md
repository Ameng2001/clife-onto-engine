# ontology-versioning Specification

## Purpose
TBD - created by archiving change add-ontology-versioning-and-replay. Update Purpose after archive.
## Requirements
### Requirement: 本体快照成不可变可寻址版本
系统 SHALL 提供 `snapshot_ontology(registry, ontology_id, version)`：把某本体在当时的五要素定义（Object/Link/Function/Rule/Action）与相关映射冻结成一个 `OntologyVersion`。该版本 MUST 可寻址（按 (ontology_id, version)）且其 registry 可被 `ActionEngine` 直接解析执行。

#### Scenario: 快照可执行
- **WHEN** 对 grass 当前 registry 做 `snapshot_ontology(reg, "grass", "grass@0.1.0")`
- **THEN** 得到 OntologyVersion，其 registry 能 `get_action("grass","出一地一方")`，可喂给 ActionEngine 跑 validate

### Requirement: 版本不可变
快照后对活 registry 的增改 MUST NOT 影响已快照的版本。

#### Scenario: 活 registry 变更不回溯污染旧版本
- **WHEN** 快照出 v1 后，往活 registry 新注册一个 Action
- **THEN** v1 的 registry 里查不到该新 Action（版本冻结在快照时刻）

### Requirement: 多版本共存
`OntologyVersionStore` SHALL 按 (ontology_id, version) 持有多个版本、支持 put/get/list，版本之间互不影响。

#### Scenario: 存取多版本
- **WHEN** put 了 grass@0.1.0 与 grass@0.2.0
- **THEN** 各自 get 回来是独立快照；list 能列出两者

