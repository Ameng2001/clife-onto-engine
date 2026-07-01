## 1. SqliteMemoryStore

- [x] 1.1 `memory/sqlite_store.py`：`SqliteMemoryStore(MemoryStore)` write-through；建表 + 启动加载；item 序列化（enum→value/tuple→list）
- [x] 1.2 覆写 add/access/record_action_outcome/on_rule_change/demote_stale：父类逻辑后写穿受影响条目

## 2. 测试 + smoke

- [x] 2.1 `tests/test_sqlite_memory.py`：重开恢复；access hit_count 持久；by_layer 继承；on_rule_change 级联持久
- [x] 2.2 `scripts/smoke_sqlite_memory.py`：add→重开恢复 + access 持久

## 3. 收尾

- [x] 3.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 3.2 README §16 路线图勾上「记忆持久层（SqliteMemoryStore）」
- [x] 3.3 `openspec validate add-sqlite-memory-store --strict`
