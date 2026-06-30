## Why

clife-onto-engine 是受治理的**写**半区(OAG:Action 引擎 guard→写后规则→确定性回滚→审计),但它**刻意做薄**了读/发现/可视化/agent 接入这半区——目前对外只有 HTTP `/ask` 和离线 OKF viz,没有交互式对象图浏览、没有标准 agent 读契约(MCP)、没有多语言读 SDK。

Alibaba UModel 恰好是一个 vendor-neutral 的语义**读**运行时(YAML model pack + SPL `.umodel/.entity/.topo` + MCP 读工具 + Web Explorer + 遥测 query-plan + 3 语言 SDK),强在我们薄的地方。两者几乎零重叠,是"企业语义 OS"的两个互补半区。已就深度使用达成 license 协议。**现在**接它,可以零内核侵入地白捡一整套读/可视化/agent 接入层,且完全踩在既有"本体是底座、skill/agent 是调用方"的分层叙事上——查路径是"OAG 基底上的结构化受控读、非 RAG"。

## What Changes

- 新增**行业无关导出器** `clife_onto_engine/umodel.py`(与 `okf.py` 同构):五要素 registry → UModel YAML model pack。`ObjectType→entity_set`、`LinkType→entity_set_link`、映射注册表(槽位2)→ `data_link`+`storage_link`、运行时实例 → `entities.json`/`relations.json`。
- 新增 `scripts/export_umodel.py`(grass registry → pack 落盘)与 `scripts/smoke_umodel.py`(离线校验导出 pack 合 UModel schema)。
- 将 UModel server 作为平台**官方读层**纳入 `docker-compose.yml`(默认起的 `umodel-server` 服务,非可选 profile),消费导出的 pack;人工在 Explorer(:5173)验收治理对象图。
- vendor UModel 的只读 schema 规格到 `third-party/umodel-schemas/`(纯为离线/CI 校验,不依赖起 Go 服务)。
- 新增定位文档 `docs/04-umodel-interop.md`:UModel = 读层 vs 引擎 = 写层的分层纪律 + 契约映射表 + 红线(对齐 02/03 的纠偏卡风格)。
- **非破坏**:不改内核任何模块,内核纯净 CI(`check_kernel_purity.py`)照常通过;UModel 走独立进程,不引入 Go 依赖、不进 Python import 路径;引擎不依赖 UModel 即可运行(读层纯增量、可关)。

## Capabilities

### New Capabilities
- `umodel-pack-export`: 五要素 registry(含映射注册表与运行时实例)无损编译成 UModel model pack(entity_set / entity_set_link / data_link / storage_link / entities / relations),离线确定性、可对 vendored schema 校验、行业无关。
- `umodel-read-layer`: 把 UModel server 作为引擎之上的官方只读交互层运行(compose sidecar,默认起),装载导出 pack,提供 Web Explorer 浏览、SPL 受控读与 MCP 读工具接入;与引擎写路径解耦、可独立关停。

### Modified Capabilities
<!-- openspec/specs/ 当前为空(greenfield 互操作),本变更不改动任何既有 spec 级需求。 -->

## Impact

- **新增代码**:`clife_onto_engine/umodel.py`、`scripts/export_umodel.py`、`scripts/smoke_umodel.py`。
- **配置/资产**:`docker-compose.yml`(+umodel-server 服务)、`third-party/umodel-schemas/`(vendored 只读规格)、`docs/04-umodel-interop.md`。
- **依赖**:不新增 Python 运行时依赖(导出器仅用 PyYAML,已在 requirements);UModel 以容器服务形态引入,不进源码树、不进构建链。
- **红线守护**:内核纯净 CI 不受影响(导出器行业无关、与 `okf.py` 同层);**绝不**把 UModel 的 Go server/query/web 源码 vendor 进本仓库(工程负担,非 license 问题)。
- **明确推迟(本提案不含,留作 phase 2)**:`umodel-governed-write-bridge` —— 给 UModel 加 `entity_write` MCP 写工具代理回 Action 引擎,使 agent 在 UModel 内既读对象图又触发受治理的写(两个半区合体的完整 OAG demo)。本提案先把读互操作做扎实。
