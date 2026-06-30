## Context

phase 2 的 `GovernedBridge.act` 提交后只反映对象(`ActionResult.written`)。`Capability.stage_link` 已支持 Action 写关系,`ActionEngine` commit 已落 `StagedLink`(action_engine.py 已遍历 changeset 的 StagedLink 写库),但 `ActionResult` 不暴露已提交关系,故桥无从反映。`ActionResult` 在 `kernel/rejection.py`,由 `action_engine.py` 在提交分支构造(已从 changeset filter StagedWrite 填 `written`)。

## Goals / Non-Goals

**Goals:**
- `ActionResult` 暴露已提交关系;桥提交后也反映关系进 UModel 读层(`.topo` 可见)。
- 关系两端 id 与对象反映同公式(确定性 32-hex),引用闭合。

**Non-Goals:**
- 不替任何插件决定"哪个 Action 写哪条关系"(建模决策,留插件);本变更只做引擎机制 + 桥反映。
- 不改 read-only 红线:仍只反映 committed;rejected/pending_hil 零反映;反映失败不回滚。
- 不改 `stage_link`/commit 既有语义。

## Decisions

### D1. `ActionResult.links_written` 加 additive 字段(默认空)
`tuple[tuple[str,str,str,str,str], ...]` = `(link_type, from_type, from_key, to_type, to_key)`。默认 `()` → 既有用法/不写关系的 Action 完全不受影响(向后兼容)。**备选**:复用 `written` 混装——否,对象/关系结构不同,分字段清晰。

### D2. 在 `action_engine.py` 与 `written` 同处填充
提交分支构造 `ActionResult` 时,从 `ctx.changeset` filter `StagedLink` 填 `links_written`,与既有 `written` filter `StagedWrite` 对称。**备选**:commit 时单独收集——否,同处一次遍历最简、最不易漂移。

### D3. `Reflector.reflect_relations` 复用对象反映的 id 公式
每条已提交关系 → UModel relation payload(`__src_entity_id__`/`__dest_entity_id__` = `_eid(domain, type, key)`,带 `__relation_type__`/观测时间窗)→ REST `relations:write`。两端 id 与 `reflect`(对象)同公式 → 引用闭合。**备选**:让 UModel 自己算 id——否,必须与对象反映用的 id 一致才能连上。

### D4. 桥先反映对象、再反映关系(关系依赖端点存在)
`act` committed 时:先 `reflect`(对象)、后 `reflect_relations`(关系)——关系两端实体须先在读层存在。两步任一失败都只记录、不回滚引擎提交(D 红线不变)。

## Risks / Trade-offs

- [关系端点实体未先反映 → relations:write 失败] → 同一次 act 的对象先反映(D4);跨 act 的端点由其各自 act 反映/全量 `export_umodel.py` 兜底。
- [触及内核 ActionResult] → additive 字段 + 默认空 → 向后兼容;既有 28+ 测试不受影响(回归验证)。
- [关系反映失败遮蔽对象反映成功] → 结果分别记 `reflected`/`relations_reflected`/`reflect_error`,不互相吞。

## Migration Plan

纯 additive:加字段 + 填充 + 反映方法 + act 一步。回滚 = 还原三处。无数据迁移;不写关系的 Action 零感知。

## Open Questions

- 关系的 `__entity_id__` 端点类型来自 `StagedLink.from_type/to_type`(裸名)——与对象反映的 `_eid(domain, type, key)` 一致即可,无歧义。
- 在线验收需一个写关系的 Action;grass 现无,故在线脚本暂不覆盖关系(单测用测试内最小 Action 覆盖),与 docs §7 一致。
