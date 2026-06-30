## 1. 引擎机制：ActionResult 暴露已提交关系

- [x] 1.1 `kernel/rejection.py`：`ActionResult` 增 `links_written: tuple[tuple[str,str,str,str,str], ...] = ()`（additive）
- [x] 1.2 `kernel/action_engine.py`：提交分支构造 ActionResult 时，从 changeset filter `StagedLink` 填 `links_written`（与 `written` 同处）

## 2. 桥反映关系

- [x] 2.1 `mcp/bridge.py` `Reflector.reflect_relations(links)`：成形 relation payload（`_eid` 两端 + `__relation_type__` + 观测时间窗）→ REST `relations:write`
- [x] 2.2 `GovernedBridge.act`：committed 时先反映对象、后反映关系（`links_written` 非空才反映）；结果分记 `reflected`/`relations_reflected`/`reflect_error`
- [x] 2.3 rejected/pending_hil 仍零反映（对象与关系皆不）；反映失败不回滚提交

## 3. 测试（不改 grass 插件）

- [x] 3.1 `tests/test_mcp_bridge.py`：测试内注册一个写关系的最小 Action（`stage_write` + `stage_link`），断言 `act` committed 后 `links_written` 暴露、`reflect_relations` 被调用、payload 两端 id 与对象一致
- [x] 3.2 断言该 Action 被拒/HIL 时关系零反映
- [x] 3.3 回归：既有 45 测试 + smoke 全绿（additive 字段向后兼容）

## 4. 收尾

- [ ] 4.1 `scripts/smoke_mcp_bridge.py` 补一例关系反映（可选，复用测试 Action）
- [x] 4.2 docs/04 §7：把"关系反映"从 TODO 移到「已实现」
- [x] 4.3 `check_kernel_purity.py` 通过；`openspec validate add-relation-reflection --strict`
