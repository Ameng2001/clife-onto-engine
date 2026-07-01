## Context

GraphStore 有 `iter_objects(type)`（对象实例）与 `_edges`（StagedLink 关系实例）。OKF 导出器/viz 是**概念层**（schema），用 vendored cytoscape 渲染。本 Explorer 复用同一 vendored cytoscape，但渲染**实例层**（运行时对象图）。web.py 已有"工厂注入 compiler"的模式——第三方资产同样由调用层注入，保持 kernel 纯净。

## Goals / Non-Goals

**Goals:** 从 store 渲染运行时对象图（实例+关系）为自包含离线 HTML（类型上色+检视+图例）；静态导出 + 活端点两形态；kernel 纯净、零新依赖。

**Non-Goals:** 不重写 OKF 概念图；不做编辑（只读浏览）；不做后端时序图（那是遥测读的 plan，不在图里）；本期不做复杂筛选/搜索 UI（留扩展）。

## Decisions

### D1. `explorer.py` 第三方无关：cytoscape JS 由调用层注入
`render(..., cytoscape_js="")`：给了就内联（离线自包含），没给则留占位（测试可不内联）。kernel 模块**不 import、不读 third-party 路径**——JS 由 `scripts/export_explorer.py`/`serve.py` 读 vendored 后传入。**备选**:render 直接读 third-party——否，破 kernel 与 third-party 的边界，且不可注入测试。

### D2. 节点/边数据 = registry 声明的类型 × store 实例
遍历本 ontology 每个 ObjectType 的 `iter_objects` → 节点(id=`type:key`，label 取 name-ish 字段或主键，otype，props)；`store._edges` 过滤两端类型属本 ontology → 边(source/target 同 id 规则，label=link_type)。与导出器 `_eid`/`_qualified` 同 id 约定思路(此处用可读 `type:key` 作 DOM id)。

### D3. 类型上色 + 图例：稳定调色板
按 ObjectType 名稳定取色（预置调色板 + 按名 hash 兜底），节点着色、图例列类型→色。沿用 OKF viz 的"按类型上色 + 图例"体验，但对象类型是插件声明的，故用稳定 hash。

### D4. 检视面板：点节点看属性
右侧 panel，点节点 → 显示其 `props`（属性表）。纯前端(内联 JS)，数据已随 HTML 内嵌，离线可用。

### D5. 活端点 `GET /explorer/{ontology}` 渲染活 store
web.py `create_app(..., explorer_js="")`；端点从 `backends[ontology].store` 现场 render → `text/html`。浏览**实时治理状态**（做完一个 Action 刷新即见新对象），不需 UModel。`serve.py` 读 vendored cytoscape 注入。**备选**:只静态导出——加活端点才真正替代 UModel Explorer 的"看实时"。

## Risks / Trade-offs

- [cytoscape 365KB 内联 → HTML 体积] → 可接受（离线自包含的代价，同 OKF viz）；活端点每次内联，量级 <1MB。
- [props 含敏感字段] → Explorer 是只读浏览，展示 store 现有字段；密级过滤留后续（与映射层 classification 打通）。
- [大图性能] → cytoscape cose 布局对中小图足够；超大实例集的分页/筛选留扩展。
- [触及 web.py] → `/explorer` 纯新增、`explorer_js` 可选默认空；`/ask` 等不变。

## Open Questions

- 是否同时渲染"对象↔遥测序列"提示（点节点显示它有哪些 metric/log 绑定，可跳 /plan）？倾向本期只做对象图，遥测联动留下一块。
- 搜索/按类型过滤 UI 是否本期做？倾向最小（图例点击高亮足够），复杂筛选留扩展。
