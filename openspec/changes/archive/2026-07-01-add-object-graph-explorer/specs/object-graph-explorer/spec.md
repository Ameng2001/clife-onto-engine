## ADDED Requirements

### Requirement: 从 GraphStore 渲染运行时对象图为自包含 HTML
系统 SHALL 提供 `render(registry, store, ontology_id, *, cytoscape_js, title)`：遍历本 ontology 每个 ObjectType 的实例为节点（按类型上色）、关系实例为边，产出自包含 HTML（图 + 实例检视 + 类型图例）。render MUST 行业无关且第三方无关——cytoscape JS 由调用层注入，模块不读 third-party 路径。

#### Scenario: 渲染实例与关系
- **WHEN** 对含 Site/parcel_001 及若干关系的 store 调用 render
- **THEN** 产出 HTML 内嵌该实例节点与其关系边；节点带类型与属性；含类型图例

#### Scenario: 注入 JS 即离线自包含
- **WHEN** render 传入 vendored cytoscape JS
- **THEN** 产出 HTML 内联该 JS，无任何 `src="https` 外链（完全离线单文件）

#### Scenario: 行业无关
- **WHEN** 运行 `check_kernel_purity.py`
- **THEN** `clife_onto_engine/explorer.py` 无行业词汇，检查通过

### Requirement: 静态离线导出
系统 SHALL 提供 `scripts/export_explorer.py`：读 vendored cytoscape 内联，把各本体运行时对象图导为 `build/explorer/<ontology>.html`（离线单文件）。

#### Scenario: 导出 grass/chili
- **WHEN** 运行 export_explorer
- **THEN** 生成 grass 与 chili 的离线 Explorer HTML，各自含其对象图、无外链

### Requirement: 活服务端点浏览实时治理状态
HTTP 服务 SHALL 提供 `GET /explorer/{ontology}`：从活 store 现场渲染 HTML（`text/html`），浏览实时对象图；未知本体 404。

#### Scenario: 浏览活状态
- **WHEN** `GET /explorer/grass`
- **THEN** 返回 200 text/html，内容是当前 grass store 的对象图 Explorer

#### Scenario: 未知本体 404
- **WHEN** `GET /explorer/medical`
- **THEN** 返回 404
