## ADDED Requirements

### Requirement: 四层记忆的 SQLite 持久后端
系统 SHALL 提供 `SqliteMemoryStore(db_path)`，与内存版 `MemoryStore` **同接口**（add/get/by_layer/access/record_action_outcome/on_rule_change/demote_stale），变更 write-through 持久到 SQLite（stdlib，零依赖），`__init__` 从库加载已有条目。四层逻辑复用父类。行业无关、可直接注入 Session 替换。

#### Scenario: 记忆跨重启不丢
- **WHEN** 用 SqliteMemoryStore(db) add 若干条目，再用同一 db 新建一个 SqliteMemoryStore
- **THEN** 之前的条目被加载回来（get 得到、by_layer 可查）

#### Scenario: 变更写穿持久
- **WHEN** access 某条目（hit_count++）后重开同库
- **THEN** 该条目的 hit_count 持久（新实例读到自增后的值）

#### Scenario: 四层逻辑照常
- **WHEN** 对 SqliteMemoryStore 调 by_layer / on_rule_change
- **THEN** 行为与内存版一致（复用父类逻辑），且级联变更被持久
