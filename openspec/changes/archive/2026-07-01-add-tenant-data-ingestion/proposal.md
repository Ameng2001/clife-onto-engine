## Why

真 Qwen 端到端四测都在 `seed_reference_data()` —— **代码里硬编码**的参考数据上跑。这对 demo/测试够用，但生产落地不能靠改插件代码灌数：`tenants/mengcao`（tenant-zero 问草）目前是空目录。缺的是"原型硬编码 → 产品数据接入"的接缝：租户该能**声明**自己的数据源，由引擎按本体 schema 校验后落库，脏行留痕可审、不静默丢、不崩。

补一个**租户数据接入**能力：声明式清单（`tenants/<t>/tenant.yaml`）+ 内核通用加载器（按 `ObjectType` schema 校验：必填字段、类型强制、主键落库），产出可审计 `IngestReport`（载入数 / 逐行拒绝+原因 / 每对象完备度）。与行业无关——只认 registry 里的 schema + 通用文件格式，无任何行业词。

## What Changes

- `clife_onto_engine/tenant/ingest.py`（新内核模块）：`load_tenant(manifest, registry, store)` 读清单，逐源 csv/jsonl/json 读行 → 按 `ObjectType` schema 校验（必填/类型强制）+ 主键解析（支持 `{col}::{col}` 组合模板）→ `store.put_object`；产 `IngestReport`/`ObjectIngest`（载入/拒绝+原因/完备度）。脏行逐条拒绝留痕，不静默丢、不抛崩。
- `tenants/mengcao/`：租户清单 `tenant.yaml`（本体 grass，声明 Site/NativeListing/ForageSample 三源）+ `data/*.csv` **样例数据（SAMPLE，形如真实导出）**——接真业务时换 CSV 即可。
- `scripts/tenant_load.py`：接入 harness —— 加载 → 打印报告 → 在**加载的租户数据**（非 seed）上跑该本体 CQ 套件验收。
- 测试：样例落库计数/类型强制/组合主键/完备度；脏行（缺主键/缺必填/数字非法）逐条拒绝留痕；未知对象拒绝；真数据上 CQ 全过。
- **非破坏**：纯新增；`seed_reference_data` 与既有回路不变；行业无关（内核纯净 CI）。

## Capabilities

### New Capabilities
- `tenant-data-ingestion`: 租户经声明式清单把数据源按本体 schema 校验后落库，脏行留痕可审，产可审计接入报告；替代"代码里硬编码 seed"的生产接缝。与行业无关（只认 schema + 通用格式）。

## Impact

- **新增代码**：`clife_onto_engine/tenant/`（ingest 加载器）、`tenants/mengcao/`（清单+样例数据）、`scripts/tenant_load.py`、`tests/test_tenant_ingest.py`。
- **红线守护**：加载器**行业无关**（只读 registry schema，无行业词，内核纯净 CI）；schema 校验兜底（必填/类型/主键），脏行不静默丢；样例数据明确标注 SAMPLE，不冒充真业务数据。
- **接缝**：`seed_reference_data`（demo 硬编码）↔ `load_tenant`（生产声明式，schema 校验、可审计）。
