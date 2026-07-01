## 1. 节点附遥测元数据

- [x] 1.1 `explorer.py render`：查 `registry.mappings.telemetry`，给节点 `data.telemetry=[{name,provider,kind}]`（无绑定空）
- [x] 1.2 检视面板 JS：显示 props 后列出该节点的遥测序列（名 · provider · kind）

## 2. 活端点取计划（渐进增强）

- [x] 2.1 render 注入 ontology 名；metric 序列给"取计划"按钮 → `fetch('/plan',POST)` → 显示 plan
- [x] 2.2 log 序列显示 provider/kind 提示（需 params，一键取计划留 metric）
- [x] 2.3 静态无服务：fetch 失败 catch → 提示"需活服务"，不崩

## 3. 测试

- [x] 3.1 `tests/test_explorer.py`：render 节点含 telemetry 序列（Site 有 soil_moisture/iot_alerts）；无绑定对象为空
- [x] 3.2 `tests/test_web.py`：/explorer 页面含遥测联动标记（结构断言）

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest 全绿
- [x] 4.2 docs/04 §9 Explorer 注记补"已联动遥测（点对象看序列/取计划）"
- [x] 4.3 `openspec validate add-explorer-telemetry-link --strict`
