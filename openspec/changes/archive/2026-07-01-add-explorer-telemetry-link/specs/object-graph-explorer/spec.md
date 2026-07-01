## ADDED Requirements

### Requirement: Explorer 节点联动遥测
`render` SHALL 给每个对象节点附上其对象类型的遥测序列元数据（name/provider/kind，查 `registry.mappings.telemetry`；无绑定则空）；检视面板 SHALL 列出这些序列。附遥测仍 MUST 只读、行业无关。

#### Scenario: 有遥测绑定的节点展示序列
- **WHEN** render 一个绑定了 metric/log 序列的对象（如 Site）
- **THEN** 该节点数据含 telemetry 序列（名/provider/kind），HTML 检视区可据此列出

#### Scenario: 无绑定节点不受影响
- **WHEN** render 一个无遥测绑定的对象类型
- **THEN** 其节点 telemetry 为空，对象图渲染与之前一致

### Requirement: 活端点就地取查询计划
`/explorer` 活服务 SHALL 让 metric 序列可就地取计划：前端经既有 `POST /plan` 取回已代入 id 的计划并显示；静态导出无服务时 MUST 优雅降级（提示需活服务，不崩）。

#### Scenario: 活端点取 metric 计划
- **WHEN** 在 `/explorer/grass` 点某 Site 节点的 metric 序列"取计划"
- **THEN** 前端 fetch /plan 取回该对象的 PromQL（id 已代入）并显示在检视面板

#### Scenario: 静态导出优雅降级
- **WHEN** 在静态导出的 HTML（无服务）尝试取计划
- **THEN** 前端捕获失败并提示"需活服务"，页面不报错崩溃
