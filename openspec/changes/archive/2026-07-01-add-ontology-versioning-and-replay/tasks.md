## 1. 本体版本化

- [x] 1.1 `clife_onto_engine/versioning.py`：`OntologyVersion(ontology_id, version, registry)` + `snapshot_ontology(registry, ontology_id, version)`——新建只含该 ns 五要素 + mappings 的冻结 Registry
- [x] 1.2 `OntologyVersionStore`：按 (ontology_id, version) put/get/list
- [x] 1.3 不可变：快照持有当时 def 引用；活 registry 后续增改不回溯污染

## 2. 决策重放

- [x] 2.1 `clife_onto_engine/replay.py`：`replay(snapshot, registry, *, store=None, param_overrides=None) → ReplayResult`——重建 actor+params、跑 validate、算 flipped
- [x] 2.2 ReplayResult：original_decision / replay_would_commit / flipped / violations / counterfactual / against_version
- [x] 2.3 flipped 判定：original_would_commit = decision ∈ {committed,pending_hil}；反事实经 param_overrides
- [x] 2.4 validate_supported=False → 结构化 skip（不抛）

## 3. 测试 + smoke

- [x] 3.1 `tests/test_versioning_replay.py`：快照可执行 / 版本不可变 / 多版本共存；重放复现 / 反事实翻转 / 换版本换裁决 / skip
- [x] 3.2 `scripts/smoke_replay.py`：grass 一次真实 execute 落审计 → 取快照重放复现 + 反事实（非乡土翻转）+ 对更严版本重放翻转

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图：勾上「本体版本化 + 决策重放（B/C 地基）」；docs 记边界（function-backed 依赖 store，点位历史留扩展）
- [x] 4.3 `openspec validate add-ontology-versioning-and-replay --strict`
