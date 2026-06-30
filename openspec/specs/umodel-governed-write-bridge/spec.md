# umodel-governed-write-bridge Specification

## Purpose
TBD - created by archiving change add-umodel-write-bridge. Update Purpose after archive.
## Requirements
### Requirement: 引擎 MCP server 暴露受治理工具
系统 SHALL 提供一个行业无关的引擎 MCP server(`clife_onto_engine/mcp/`),暴露受治理读工具 `query` 与 opt-in 写工具 `act`。server MUST 复用 `Session`/`ActionEngine`,不在 MCP 层重复任何治理逻辑。

#### Scenario: 列出工具
- **WHEN** MCP 客户端 `tools/list`
- **THEN** 返回 `query`(读,默认启用)与 `act`(写);`act` 仅在显式开启写时出现

#### Scenario: 写工具默认 opt-in
- **WHEN** server 未开启写开关启动
- **THEN** `act` 不被注册/不可调用,只暴露读工具

### Requirement: act 全程经 Action 引擎(本体兜底)
写工具 `act(ontology, action, params, actor_role)` SHALL 把调用直送 `ActionEngine.execute`,经 guard→写后规则→提交/确定性回滚→审计快照。引擎的裁决 MUST 是最终权威——MCP 层不得旁路或覆盖。

#### Scenario: 合法且合规 → 提交
- **WHEN** `act` 调用一个已声明 Action,参数合法且不违反任何 hard 规则
- **THEN** 引擎提交,返回 `committed` 与已写入的 (type,key) 列表

#### Scenario: 合法但违规 → 确定性拒绝
- **WHEN** `act` 调用一个语法合法的 Action，但其写入违反某 hard 写后规则
- **THEN** 引擎确定性回滚,`act` 返回 `rejected` 与 `violations`(结构化,非异常)

#### Scenario: 未声明动作被拒
- **WHEN** `act` 调用一个 registry 未注册的 action 名
- **THEN** 返回结构化错误(解析失败),不产生任何写

### Requirement: 提交后仅反映已提交状态进读层
`act` 提交成功后,系统 SHALL 把 `ActionResult.written` 对应的**已提交**对象经 UModel REST `entities:write`、并把 `ActionResult.links_written` 对应的**已提交**关系经 REST `relations:write` 反映进读层 workspace(成形复用导出器 `_eid`/payload;关系两端 id 与对象反映同公式,引用闭合)。`rejected` 与 `pending_hil` MUST NOT 反映。反映对象在前、关系在后(关系端点须先存在)。

#### Scenario: 提交即反映对象
- **WHEN** `act` 返回 committed,写入了某对象实例
- **THEN** 该实例经 entities:write 进入 UModel 读层,`.entity` 查询可见;`__entity_id__` 与导出器一致(确定性 32-hex)

#### Scenario: 提交即反映关系
- **WHEN** `act` 返回 committed,且该 Action 经 `stage_link` 写了关系
- **THEN** `ActionResult.links_written` 暴露这些已提交关系,经 relations:write 进入读层;`.topo` 可遍历到;两端 `__entity_id__` 与对应对象实例一致

#### Scenario: 拒绝不反映
- **WHEN** `act` 返回 rejected
- **THEN** 读层不发生任何对象或关系写入,UModel 对象图不变

#### Scenario: HIL 待审不反映
- **WHEN** Action 命中 HIL 关口,引擎返回 pending_hil(未提交)
- **THEN** 读层不反映(对象与关系皆不);`act` 原样返回 pending_hil 供人工复核

### Requirement: 不开 UModel 写旁路 · 引擎不依赖读层
系统 MUST NOT 启用 UModel 自身的 `entity_write`/`entity_expire` 写工具——受治理写的唯一入口是引擎 `act`。引擎的提交 MUST NOT 依赖 UModel 可用性。

#### Scenario: UModel 写工具保持禁用
- **WHEN** 审视 sidecar 与 MCP 桥配置
- **THEN** UModel `entity_write`/`entity_expire` 处于 disabled;无任何绕过引擎的写路径

#### Scenario: 读层缺席不阻断治理写
- **WHEN** UModel server 不可用时调用 `act`
- **THEN** 引擎照常 guard→提交/回滚→审计;反映步骤失败仅记录,不回滚已提交的治理写

