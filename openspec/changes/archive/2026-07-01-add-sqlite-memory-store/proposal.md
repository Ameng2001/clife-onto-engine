## Why

路线图战术补丁：**记忆持久层**。四层记忆当前只在内存（`MemoryStore`），进程重启即丢——审计/journal 已有 SQLite 持久（`trust/sqlite_store.py`），记忆缺同款。补一个 `SqliteMemoryStore`，同接口、可直接注入 `Session`，让记忆跨重启不丢。

## What Changes

- 新增 `clife_onto_engine/memory/sqlite_store.py`：`SqliteMemoryStore(MemoryStore)` —— 子类 **write-through**：复用父类全部四层逻辑（by_layer/淘汰/级联作废/滑动窗口），变更时写穿 SQLite（stdlib sqlite3，零依赖），`__init__` 从库加载已有条目。与 `MemoryStore` 同接口，可直接换。
- 测试 + smoke：add 后重开同库 → 条目恢复；access 后 hit_count 持久；by_layer/装配（继承）照常；on_rule_change 级联作废持久。
- **非破坏**：纯新增；不改 `MemoryStore`/`assemble`；行业无关（内核纯净 CI）。

## Capabilities

### New Capabilities
- `memory-persistence`: 四层记忆的 SQLite 持久后端，与内存版 `MemoryStore` 同接口（write-through 复用四层逻辑），记忆跨进程/重启不丢。

## Impact

- **新增代码**：`clife_onto_engine/memory/sqlite_store.py`、`scripts/smoke_sqlite_memory.py`、`tests/test_sqlite_memory.py`。
- **红线守护**：stdlib sqlite3 零依赖；行业无关；与 trust SQLite 同模式（WAL/autocommit）。
