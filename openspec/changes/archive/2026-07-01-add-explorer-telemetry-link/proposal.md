## Why

自有 Explorer 现在只展示对象图(语义读)。但同一对象往往还绑了遥测序列(遥测读)——两块自有读在 UI 里是割裂的。把它们合体:点一个对象节点，除看属性外，还能看它有哪些遥测序列(名/provider/kind)，并**直接取到查询计划**。这才是"深读"在 UI 里的兑现:结构(对象图)+状态(遥测)一屏可达。

## What Changes

- `explorer.py` `render`：给节点附上其对象类型的遥测序列元数据(name/provider/kind)——查 `registry.mappings.telemetry`；检视面板列出这些序列。
- **活端点渐进增强**:`/explorer` 的节点检视里，metric 序列(无需运行时参数)可点"取计划"→ 前端 `fetch('/plan')` 取回已代入 id 的 PromQL 并显示;log 序列(需 params)显示提示。静态导出无服务时优雅降级(仅列序列，不可取计划)。
- 测试:render 附遥测元数据、检视含序列;活端点 fetch /plan 路径(结构断言)。
- **非破坏**:纯增量;无遥测绑定的对象节点行为不变;不改 build_plan/telemetry 机制。

## Capabilities

### Modified Capabilities
- `object-graph-explorer`: Explorer 节点**联动遥测**——展示对象的遥测序列(name/provider/kind)，活端点可就地取 metric 查询计划(经既有 `/plan`)。把语义读(对象图)与遥测读(query-plan)在同一 UI 合体。

## Impact

- **改动代码**:`clife_onto_engine/explorer.py`(节点附遥测元数据 + 检视面板 + 活端点取计划 JS)、`tests/test_explorer.py` / `tests/test_web.py`。
- **红线守护**:explorer.py 仍行业无关(只读 registry.mappings.telemetry，无行业词);取计划仍经 `build_plan`(引擎只产计划不执行);静态导出无外部调用(优雅降级)。
- **拼图**:自有深读(对象图 + 遥测)在自有展示里合体——本体 OS 的"看"这一面完整自洽。
