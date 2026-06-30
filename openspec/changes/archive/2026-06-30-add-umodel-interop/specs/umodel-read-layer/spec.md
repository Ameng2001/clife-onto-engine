## ADDED Requirements

### Requirement: UModel server 作为官方只读层运行
平台 SHALL 在 `docker-compose.yml` 中默认包含一个 `umodel-server` 服务(非可选 profile),以 `file.memory` 持久化 provider 运行,装载导出的 model pack,提供 Web Explorer、SPL 受控读与 MCP 读工具。

#### Scenario: compose 默认起读层
- **WHEN** 执行 `docker compose up`
- **THEN** `umodel-server` 随之启动,装载 grass 导出 pack,Explorer 在约定端口可访问

#### Scenario: 装载导出 pack
- **WHEN** umodel-server 启动并指向 grass 导出目录
- **THEN** `.umodel` 查询能列出 grass 的 entity_set / link,Explorer 能浏览对象图

### Requirement: 读层与引擎写路径解耦
读层 SHALL 是纯增量、可独立关停;引擎(`serve.py` / `Session.ask` / `/ask`)的启动与运行 MUST NOT 依赖 UModel server。

#### Scenario: 读层缺席不影响引擎
- **WHEN** `umodel-server` 未启动或已停止
- **THEN** 引擎的做(Action)/查(OQL)/澄清 经 `/ask` 正常工作,既有测试不受影响

#### Scenario: 治理读写仍在引擎内
- **WHEN** 通过 UModel 浏览 grass 对象图
- **THEN** 所有访问是只读;任何受治理的写仍只能经引擎 Action 引擎(guard→写后规则→回滚→审计),UModel 不提供写旁路

### Requirement: 互操作定位文档
变更 SHALL 提供 `docs/04-umodel-interop.md`,固化 UModel(读层)与引擎(写层)的分层纪律、五要素↔UModel kinds 契约映射表与红线(对齐 02/03 的纠偏卡风格)。

#### Scenario: 文档含契约映射与红线
- **WHEN** 阅读 `docs/04-umodel-interop.md`
- **THEN** 文档明确:读/写半区分工、契约映射表、"不 vendor Go 源码 / 不用 SPL 替换 OQL / 治理写不进 UModel" 的红线
