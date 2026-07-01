## ADDED Requirements

### Requirement: 声明式租户数据接入（按本体 schema 校验落库）
系统 SHALL 提供 `load_tenant(manifest, registry, store)`：读租户清单（`{tenant, ontology, sources:[{object, file, format, key?}]}`），逐源读行（csv/jsonl/json），按对应 `ObjectType` schema 校验后经 `store.put_object` 落库。校验 SHALL 含：主键解析（默认取 `primary_key` 列，或按 `key` 模板 `"{col}::{col}"` 组合）、必填字段存在、按声明类型强制（number/list/string）。不改插件代码即可灌数（对 `seed_reference_data` 的生产替代）。

#### Scenario: 样例数据按 schema 落库
- **WHEN** 对声明了 Site/NativeListing/ForageSample 三源的 mengcao 清单调用 load_tenant
- **THEN** 各源按主键落库，number 字段落成数值（非字符串），组合主键模板（region::species）可取到对象

#### Scenario: 组合主键模板
- **WHEN** 某源声明 `key: "{region}::{species}"`
- **THEN** 落库主键由行内该两列拼成（与既有参考数据键一致）

### Requirement: 脏行留痕可审、不静默丢、不崩
校验 SHALL 逐行进行：不满足（缺主键、缺必填字段、类型无法强制、对象未在本体声明）的行 SHALL 被拒绝并在 `IngestReport` 记录 `(行号, 原因)`，其余行照常落库。加载 MUST NOT 因脏行抛异常中断整源。`IngestReport` SHALL 汇总每对象的载入数、拒绝明细、完备度（已声明属性平均填充率）。

#### Scenario: 脏行逐条拒绝
- **WHEN** 某 Site 源含缺主键、缺必填 area_mu、area_mu 非数字、缺必填 region 的行
- **THEN** 这些行各自被拒绝并留原因，合法行仍落库，加载不中断、不抛崩

#### Scenario: 未声明对象被拒
- **WHEN** 清单某源的 object 未在该本体注册
- **THEN** 该源整体记为拒绝（0 落库），报告留因，不崩

#### Scenario: 完备度反映缺列
- **WHEN** 某行缺可选列
- **THEN** 该对象完备度 < 1.0（反映填充率），但行仍落库

### Requirement: 接入加载器行业无关
接入加载器 MUST 只依赖 registry 里的 `ObjectType` schema 与通用文件格式，不含任何行业专有词汇（内核纯净 CI 强制）。行业专有的对象/规则仍由插件声明；租户样例数据放 `tenants/<t>/`、明确标注 SAMPLE，不冒充真业务数据。

#### Scenario: 换本体/租户零改加载器
- **WHEN** 另一本体的租户提供其清单与数据文件
- **THEN** 同一 load_tenant 按该本体 schema 校验落库，无需改内核代码
