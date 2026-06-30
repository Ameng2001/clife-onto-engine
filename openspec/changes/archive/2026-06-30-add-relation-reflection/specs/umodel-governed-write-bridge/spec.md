## MODIFIED Requirements

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
