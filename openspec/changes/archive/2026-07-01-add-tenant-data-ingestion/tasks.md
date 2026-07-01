## 1. 内核接入加载器

- [x] 1.1 `clife_onto_engine/tenant/ingest.py`：`load_tenant(manifest, registry, store)` 读清单，逐源读行（csv/jsonl/json）
- [x] 1.2 按 `ObjectType` schema 校验：必填字段、类型强制（number/list/string）、主键解析（支持 `{col}::{col}` 组合模板）
- [x] 1.3 `IngestReport`/`ObjectIngest`：载入数 / 逐行拒绝+原因 / 每对象完备度；脏行留痕不静默丢、不崩

## 2. 租户 mengcao 清单 + 样例数据

- [x] 2.1 `tenants/mengcao/tenant.yaml`：本体 grass，声明 Site/NativeListing/ForageSample 三源
- [x] 2.2 `tenants/mengcao/data/*.csv`：样例数据（SAMPLE，形如真实导出，含一行缺可选列以现完备度）

## 3. 接入 harness

- [x] 3.1 `scripts/tenant_load.py`：加载 → 打印 IngestReport → 在加载的租户数据上跑 CQ 套件验收

## 4. 测试

- [x] 4.1 `tests/test_tenant_ingest.py`：样例落库计数 + 类型强制 + 组合主键 + 完备度
- [x] 4.2 脏行（缺主键/缺必填/数字非法）逐条拒绝留痕；未知对象拒绝；真数据上 CQ 全过

## 5. 收尾

- [x] 5.1 `check_kernel_purity.py` 通过（加载器行业无关）；全量 pytest 全绿（153）
- [x] 5.2 `openspec validate add-tenant-data-ingestion --strict`
