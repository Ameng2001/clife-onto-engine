## Context

clife-onto-engine 的内核只理解五要素(Object/Link/Function/Rule/Action),对象/关系存于 GraphStore SPI(InMemory / NebulaGraph),对外门面是 `Session.ask` + HTTP `/ask` + OKF 离线 viz。它**没有**交互式对象图浏览、没有标准 MCP 读契约、没有多语言读 SDK——这些是 UModel 的强项。

UModel 是 Go 写的 vendor-neutral 语义**读**运行时:model pack 用 YAML 声明 `entity_set`(对象类)/`*_set`(数据集)/`*_link`(关系与物理映射)/storage(后端),运行时实例存 `entities.json`/`relations.json`,读面是 SPL(`.umodel/.entity/.topo/.entity_set`),agent 面是 MCP(`query_spl_execute` 等读工具默认开、`entity_write` 写工具需 opt-in),外加 Web Explorer(:5173)与遥测 query-plan 生成。GraphStore provider 有 `memory`/`file.memory`/`local.ladybug`。

约束:① 内核纯净——导出器必须行业无关,与 `okf.py` 同层、同纪律。② 薄适配——UModel 走独立进程,不进 Python import、不进构建链、不 vendor 其 Go 源码。③ 引擎可独立运行——读层是纯增量、可关。④ license 已深度授权,vendor/搬运无 ceremony 顾虑(但工程负担判断不变)。

## Goals / Non-Goals

**Goals:**
- 五要素 registry(对象/关系 + 映射注册表 + 运行时实例)**无损**编译成 UModel model pack,离线确定性、可对 vendored schema 校验。
- UModel server 作为引擎之上的官方只读层运行(compose 默认起),装载导出 pack,Explorer/SPL/MCP 即开即用。
- 把"五要素 ↔ UModel kinds"的契约映射固化成可测试的代码 + 文档,作为 phase 2(治理写桥)的地基。

**Non-Goals:**
- **不**把 Function/Rule/Action(治理写半区)映射进 UModel——UModel 是只读层,治理永远留在引擎。最多把 Rule 的出处/约束作为只读元数据**注解**暴露给浏览(可见性,非执行)。
- **不**用 SPL 替换 OQL——OQL(JSON AST、防注入)仍是引擎内的受治理读;SPL 是外部浏览面。
- **不** vendor UModel 的 server/query/web 源码,**不**引入 Go 工具链。
- **不**在本变更做 `entity_write` 写桥(phase 2)。

## Decisions

### D1. 导出器落 `clife_onto_engine/umodel.py`,与 `okf.py` 同构同层
registry → pack 的编译是**我们的** Python 资产,行业无关(对 `check_kernel_purity.py` 透明)。复用 `okf.export_bundle` 的遍历骨架。**备选**:放进 `query/` adapter——否,那是 GraphStore SPI 的事,导出是离线产物层,与 OKF 并列更清晰。

### D2. 一个 ontology → 一个 UModel workspace;`domain` = `ontology_id`
`grass` registry 导成 workspace `grass`,所有 entity_set 的 `metadata.domain` = `grass`,延续引擎的 space-per-ontology 隔离语义。**备选**:多 ontology 共用一 workspace 靠 domain 区分——否,workspace 边界对齐租户隔离更干净。

### D3. 五要素 → UModel kinds 契约映射

| 五要素 | UModel kind | 说明 |
|---|---|---|
| `ObjectType`(+ 属性) | `entity_set`(`spec.fields`) | `primary_key_fields`/`id_generator` 取对象主键;`name_fields` 取展示字段 |
| `LinkType`(有向、边语义) | `entity_set_link` | `src`/`dest` = 两端 ObjectType;关系类型 = Link 名;边属性 → link fields |
| 映射注册表 槽位2(对象→物理表/列) | `data_link` + `storage_link` + storage 定义 | 对象→数据集 `data_link.fields_mapping`;数据集→后端 `storage_link.fields_mapping`;虚拟/物化/MDO 落 storage kind |
| 运行时对象实例 | `entities.json` | 每实例一条,带 `__entity_id__` |
| 运行时关系实例 | `relations.json` | src/dest/relation |
| `Function` / `Rule` / `Action` | **不映射**(只读注解可选) | 治理写留引擎;Rule 出处可作 entity_set 只读元数据 |

### D4. 装载方式:导出目录 + `file.memory` provider,sidecar 启动时挂载
导出器产出 UModel 期望的目录布局(`umodel/<domain>/{entity_set,link,...}/*.yaml` + `sample-data/{entities,relations}.json`)。compose 里 `umodel-server --graphstore file.memory --data /data`,把导出目录挂进去,或启动后调 `POST /api/v1/umodel/{ws}/import`。**备选**:走 REST `elements` 批量写——import 路径更贴合"整 pack 装载",首选 import,REST 写留作增量同步。

### D5. 离线校验优先,在线校验可选
smoke(`scripts/smoke_umodel.py`)对 **vendored `third-party/umodel-schemas/`** 做结构校验,**不**需要起 Go 服务,贴合"离线确定性 CI"。sidecar 起着时额外可跑 `umctl umodel validate` 做权威校验。**备选**:只靠在线 validate——否,会让 CI 依赖 Go 服务,违反离线纪律。

### D6. UModel server 默认起(非 `--profile`)
深度协议下读层是第一公民,不是试探性附件。compose 默认包含 `umodel-server`;但**引擎自身**(`serve.py`)启动不依赖它——读层挂了引擎照常做/查。

## Risks / Trade-offs

- [pack schema 字段对不齐,`validate` 不过] → 先 vendor `schemas/` 逐字段核,导出器对照写;smoke 离线校验早暴露;允许 1–2 轮迭代收敛。
- [UModel schema 随上游版本漂移] → vendored schema 钉版本号 + 记 commit;导出器对单一钉定版负责;升级是显式动作。
- [运维耦合:多一个 Go 服务] → 读层可关、引擎不依赖它;sidecar 仅做展示/agent 读,不在写关键路径。
- [把 Rule/Action 误暴露成 UModel 可"执行"的东西] → 契约映射显式排除治理写(D3);只读注解明确标注"metadata, not enforcement"。
- [domain/id 命名冲突] → workspace=ontology_id、domain=ontology_id 强隔离;`__entity_id__` 由对象主键确定性派生,保证导出可重放。

## Migration Plan

纯增量、无迁移:① 加导出器 + smoke(不碰内核);② vendor schema;③ compose 加 sidecar;④ 写 docs/04。回滚 = 移除 sidecar 服务 + 文件,引擎与既有 28 项测试不受影响。

## Open Questions

- 运行时实例的 `__entity_id__` 生成策略:直接复用对象主键串,还是按 UModel `id_generator` 约定派生?(倾向前者,导出确定性优先)
- Rule 只读注解要不要在本变更就做,还是并入 phase 2 写桥一起?(倾向推迟,保持本变更聚焦读)
- 多跳关系在 Explorer 的呈现:`entity_set_link` 是否需要补 `runbook_set` 才能让 RCA 式 skill 跑通?(本变更只保对象图浏览,RCA 留后续)
