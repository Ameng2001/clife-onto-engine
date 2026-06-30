## ADDED Requirements

### Requirement: 五要素 registry 编译成 UModel model pack
导出器 SHALL 将一个 ontology 的五要素 registry 编译成一个 UModel model pack:`ObjectType` 映射为 `entity_set`、`LinkType` 映射为 `entity_set_link`、映射注册表条目映射为 `data_link` + `storage_link` + storage 定义。导出器 MUST 行业无关,与 `okf.py` 同层,且不引用任何插件领域词汇(`check_kernel_purity.py` 通过)。

#### Scenario: 对象类导成 entity_set
- **WHEN** registry 含 `ObjectType` `Site`(属性 parcel_id/region/site_type,主键 parcel_id)
- **THEN** 导出 pack 含一个 `kind: entity_set`,`metadata.name` 源自对象名,`spec.fields` 覆盖全部属性,`primary_key_fields` 含主键

#### Scenario: 有向关系导成 entity_set_link
- **WHEN** registry 含 `LinkType` `treated_by`(Site→Method)
- **THEN** 导出 pack 含一个 `kind: entity_set_link`,`src`/`dest` 指向两端 entity_set,关系类型 = Link 名

#### Scenario: 映射注册表导成 data_link/storage_link
- **WHEN** 某 ObjectType 在映射注册表声明 对象→物理表/列(虚拟/物化/混合)
- **THEN** 导出 pack 含对应 `data_link`(对象→数据集 `fields_mapping`)、`storage_link`(数据集→后端 `fields_mapping`)与 storage 定义

#### Scenario: 治理写要素不被映射
- **WHEN** registry 含 `Function`/`Rule`/`Action`
- **THEN** 导出 pack 不产生任何可执行的 UModel 元素(治理写留引擎);Rule 至多以只读元数据注解出现,且标注为 metadata 而非 enforcement

### Requirement: 运行时实例导成 entities/relations
导出器 SHALL 将 GraphStore 中的运行时对象实例与关系实例导成 UModel 期望的 `entities.json` / `relations.json`,每个实例带确定性派生的 `__entity_id__`。

#### Scenario: 对象实例导出
- **WHEN** GraphStore 含对象实例 `Site/parcel_001`
- **THEN** `entities.json` 含一条记录,`__entity_id__` 由对象主键确定性派生,重复导出结果一致

#### Scenario: 关系实例导出
- **WHEN** GraphStore 含关系实例 `parcel_001 -suffers-> 盐碱`
- **THEN** `relations.json` 含一条 src/dest/relation 记录,两端 id 与 entities 对齐

### Requirement: 导出目录布局与隔离
导出器 SHALL 产出 UModel 可装载的目录布局(`umodel/<domain>/{entity_set,link,storage,...}/*.yaml` + `sample-data/{entities,relations}.json`),其中 `domain` 与 workspace 名均取 `ontology_id`,延续 space-per-ontology 隔离。

#### Scenario: 单 ontology 单 workspace
- **WHEN** 导出 `grass` registry
- **THEN** 产物 workspace 名为 `grass`,所有 entity_set 的 `metadata.domain` 为 `grass`

### Requirement: 离线 schema 校验
系统 SHALL 提供对导出 pack 的离线结构校验,校验依据是 vendored 的 UModel schema 规格(`third-party/umodel-schemas/`),且 MUST NOT 依赖启动 UModel 的 Go 服务。

#### Scenario: 合规 pack 通过离线校验
- **WHEN** 对 grass 导出 pack 运行 `scripts/smoke_umodel.py`
- **THEN** 校验对照 vendored schema 通过,退出码 0,全程无网络/无 Go 进程

#### Scenario: 缺字段 pack 被离线校验拦截
- **WHEN** 导出 pack 缺失某 entity_set 的必填 `metadata.name`
- **THEN** 离线校验失败并指出违规元素与字段
