## Why

目前唯一还实质依赖 UModel 的是**可视化浏览 UI**(Web Explorer)——想看治理对象图长啥样，还得起 UModel sidecar。要让本体 OS **自有展示**、不依赖外部就能浏览运行时对象图，需要一个自有 Explorer。

契合仓库 ethos:**完全离线、单文件、零构建**(同 OKF viz)。仓库已 vendored `cytoscape.min.js`，内联即可离线。做完这块，UModel 就只剩纯互操作(import-export)的角色，展示彻底自有。

区别于 OKF viz:OKF 渲染的是**本体概念**(对象/规则/动作 schema 层)；本 Explorer 渲染**运行时对象图**(真实实例 + 关系)——即你会开 UModel Explorer 去看的那个东西。

## What Changes

- 新增 `clife_onto_engine/explorer.py`：`render(registry, store, ontology_id, *, cytoscape_js="", title="")` —— 从 GraphStore 收对象实例(节点，按类型上色)+ 关系实例(边)，产出**自包含 HTML**(cytoscape 图 + 实例检视面板 + 类型图例)。**行业无关**、**第三方无关**(cytoscape JS 由调用层注入 → kernel 纯净)。
- 新增 `scripts/export_explorer.py`：读 vendored cytoscape 内联 → grass/chili 运行时对象图 → `build/explorer/<ont>.html`(离线单文件)。
- `web.py`：`create_app(..., explorer_js="")` + `GET /explorer/{ontology}` —— 从**活 store** 渲染 HTML(浏览**实时治理状态**，不需 UModel)；`serve.py` 读 vendored JS 注入。
- 测试:render 产出含实例/边、离线(无外链)、行业无关;`/explorer` 端点(fastapi 在时)。
- **非破坏**:纯新增模块/端点;不改五要素/OQL/Action;`create_app` 加可选参数(默认空，向后兼容)。

## Capabilities

### New Capabilities
- `object-graph-explorer`: 自有的运行时对象图浏览器——从 GraphStore 渲染实例+关系为自包含离线 HTML(类型上色 + 实例检视 + 图例)，静态导出与活服务端点两种形态；行业无关、离线单文件、零新依赖(复用 vendored cytoscape)。替代对 UModel Explorer 的浏览依赖。

## Impact

- **新增/改动代码**:`clife_onto_engine/explorer.py`、`scripts/export_explorer.py`、`web.py`(+/explorer、+explorer_js 注入)、`scripts/serve.py`(读 vendored JS)、`tests/`。
- **依赖**:零新依赖——复用 `third-party/okf-visualizer/.../vendor/cytoscape.min.js`(第三方 JS 由调用层注入，kernel 模块不触 third-party 路径)。
- **红线守护**:explorer.py 行业无关(内核纯净 CI)、第三方无关(JS 注入)；完全离线(内联 JS，无 CDN)；只读渲染，不写。
- **战略意义**:自有展示落地后，展示彻底自有，UModel 退为纯互操作。自有语义面(语义读+遥测读+治理写+审计)+ 自有展示 = 完整本体 OS。
