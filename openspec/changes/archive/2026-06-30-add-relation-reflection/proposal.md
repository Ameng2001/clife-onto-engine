## Why

治理写桥（phase 2）提交后只把**对象**反映进 UModel 读层;若一个 Action 经 `Capability.stage_link` 写了**关系**,这些关系不会同步到读层——`.topo` 看不到新拓扑。`stage_link` 已是成熟能力(引擎 commit 已处理 StagedLink),只是 `ActionResult` 没把已提交的关系暴露出来供反映。补齐它,让受治理写产生的拓扑也即时可见。

严守内核/插件分离:本变更只做**引擎机制**(把已提交 staged links 暴露 + 桥反映),**不**替任何插件发明"哪个 Action 写哪条关系"(那是建模决策)。

## What Changes

- `ActionResult` 增 `links_written` 字段(additive,默认 `()`):已提交的 staged links `(link_type, from_type, from_key, to_type, to_key)`。
- `ActionEngine` 在构造 `ActionResult` 时,从 changeset 的 `StagedLink` 填充 `links_written`(与 `written` 同处)。
- `Reflector` 增 `reflect_relations`:把已提交关系成形为 UModel relation payload(复用 `_eid`/观测时间窗)→ REST `relations:write`。
- `GovernedBridge.act`:committed 时,反映对象后**也反映关系**(若 `links_written` 非空);rejected/pending_hil 仍零反映。
- **非破坏**:`links_written` 默认空 → 既有 `ActionResult` 用法不变;不写关系的 Action 行为不变;不改任何插件。

## Capabilities

### New Capabilities
<!-- 无新 capability：扩展既有写桥行为。 -->

### Modified Capabilities
- `umodel-governed-write-bridge`: 提交后反映**也覆盖关系**——`act` 把已提交 staged links 经 `relations:write` 反映进读层;拒绝/HIL 仍零反映,read-only 红线不变。

## Impact

- **改动代码**:`clife_onto_engine/kernel/rejection.py`(ActionResult +字段)、`clife_onto_engine/kernel/action_engine.py`(填充)、`clife_onto_engine/mcp/bridge.py`(reflect_relations + act 反映关系)。
- **测试**:`tests/test_mcp_bridge.py` 增"写关系的 Action → links_written 暴露 + 关系反映"(用测试内注册的最小 Action 写一条 link,不动 grass 插件)。
- **红线守护**:仍只反映已提交;关系两端 `__entity_id__` 与对象反映同公式(确定性 32-hex),引用闭合;反映失败不回滚提交。
- **内核改动**:`ActionResult` 加字段是 additive、内核纯净(无行业词);触及"心脏"但向后兼容。
