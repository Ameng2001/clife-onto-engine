## 1. 缺口审计

- [x] 1.1 `clife_onto_engine/gaps.py`：`Gap`/`GapReport` + `audit_gaps(registry, ontology_id)`
- [x] 1.2 blocking：action_no_handler / dangling_rule_ref（guard+post_rule）/ dangling_write / function_no_impl / dangling_link_endpoint
- [x] 1.3 advisory：rule_no_source；`ok` = 无 blocking；summary

## 2. 测试 + smoke

- [x] 2.1 `tests/test_gaps.py`：grass 无 blocking；构造无 handler/悬空引用/悬空端点 → 精确定位；advisory 报 source 缺口
- [x] 2.2 `scripts/smoke_gaps.py`：grass 审计（无 blocking + advisory 清单）+ 残缺版本 blocking 定位

## 3. 收尾

- [x] 3.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 3.2 README §16 路线图勾上「本体治理缺口审计（C1 运行时侧）」
- [x] 3.3 `openspec validate add-ontology-gap-audit --strict`
