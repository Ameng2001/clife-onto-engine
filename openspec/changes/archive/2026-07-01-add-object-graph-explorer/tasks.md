## 1. 渲染器（kernel，行业无关·第三方无关）

- [x] 1.1 `clife_onto_engine/explorer.py`：`render(registry, store, ontology_id, *, cytoscape_js="", title="")`——收实例节点（类型上色）+ 关系边
- [x] 1.2 节点 label 取 name-ish 字段或主键；props 内嵌供检视；边 label=link_type；只含本 ontology 引用闭合的边
- [x] 1.3 稳定调色板（预置 + 按类型名 hash 兜底）+ 类型图例
- [x] 1.4 内联注入的 cytoscape JS → 无外链（离线自包含）；检视面板（点节点看 props）

## 2. 静态导出

- [x] 2.1 `scripts/export_explorer.py`：读 vendored cytoscape 内联 → grass/chili → `build/explorer/<ont>.html`
- [x] 2.2 打印节点/边计数 + 离线自检（无 `src="https`）

## 3. 活端点

- [x] 3.1 `web.py`：`create_app(..., explorer_js="")` + `GET /explorer/{ontology}`（text/html，活 store），未知本体 404
- [x] 3.2 `scripts/serve.py`：读 vendored cytoscape 注入 create_app

## 4. 测试

- [x] 4.1 `tests/test_explorer.py`：render 含实例/边、注入 JS 即无外链、行业无关（不含行业词的断言由 purity CI 保证，这里断言结构）
- [x] 4.2 `tests/test_web.py`：`GET /explorer/grass` 200 text/html 含对象；未知本体 404（fastapi 在时）

## 5. 收尾

- [x] 5.1 `check_kernel_purity.py` 通过；全量 pytest 全绿
- [x] 5.2 docs/04 §9：自有展示从"中长期"标注为「已落（离线单文件 + 活端点）」；README 命令清单加 export_explorer
- [x] 5.3 `openspec validate add-object-graph-explorer --strict`
