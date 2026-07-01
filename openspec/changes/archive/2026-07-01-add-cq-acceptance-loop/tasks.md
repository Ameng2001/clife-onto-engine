## 1. CQ 内核

- [x] 1.1 `clife_onto_engine/cq.py`：`ActionCQ`（name/ontology/action/params/actor_role/expect/expect_rule）+ `QueryCQ`（name/ontology/oql/min_rows）
- [x] 1.2 `run_cq_suite(cqs, registry, *, store=None) → CQReport`——动作走 validate、查询走 oql_execute，判 pass/fail
- [x] 1.3 `CQResult` / `CQReport`（计数 + 明细 + summary）；不支持预演/异常 → 该 CQ fail 并注明

## 2. grass CQ 套件（插件·槽位7）

- [x] 2.1 `plugins/grass` 加一组 CQ：合规草种→commit、非乡土→reject·乡土合规、越权角色→reject、某查询→有行

## 3. 测试 + smoke

- [x] 3.1 `tests/test_cq.py`：套件对当前版本全 pass；对"去掉乡土合规的版本"→相应 CQ fail（回归被抓）；查询 CQ 行数；报告计数
- [x] 3.2 `scripts/smoke_cq.py`：grass CQ 套件跑当前版本 pass + 对缺规则版本 fail

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过（cq.py 内核无行业词；grass CQ 在插件）；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图勾上「CQ 验收回路（C3）」；docs 记 B+C 弧闭环
- [x] 4.3 `openspec validate add-cq-acceptance-loop --strict`
