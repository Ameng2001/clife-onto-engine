## Context

`explorer.py render` 已产对象图 HTML（节点含 otype/props）。`registry.mappings.telemetry` 持对象→遥测序列绑定（每 series 有 name/provider/kind）。`/plan`（POST）已能据对象取查询计划。现要在 Explorer 把遥测联动进来。

## Goals / Non-Goals

**Goals:** 节点附遥测序列元数据；检视面板列序列；活端点就地取 metric 计划（经 /plan）；静态导出优雅降级。

**Non-Goals:** 不改 build_plan/绑定机制；不在静态 HTML 内联真实指标数据（那要连后端）；log 序列的运行时 params 输入 UI 留最简（先只 metric 一键取计划）。

## Decisions

### D1. 节点元数据附遥测序列（render 时查绑定）
每节点 `data.telemetry = [{name, provider, kind}]`（该对象类型的绑定序列，无绑定则空）。检视面板据此列出。render 仍**只读** registry.mappings.telemetry，行业无关。

### D2. 活端点取计划：前端 fetch('/plan')，metric 优先
检视面板里每个 **metric** 序列给"取计划"按钮 → `fetch('/plan',{POST, {ontology,object_type,key,series}})` → 显示 `resolved` 的 plan。**log** 序列需 params，先只显示 provider/kind 提示（一键取计划留 metric）。**备选**:内联参数输入框——留后续，先把 metric 一键打通。

### D3. 静态导出优雅降级
静态 HTML 无服务：fetch 失败即在面板显示"需活服务(/explorer)"。ontology 名注入 HTML（render 已知），object_type/key 从节点 data 取。

## Risks / Trade-offs

- [静态文件点"取计划"报错] → JS catch → 友好提示"需活服务"，不崩。
- [render 触及 mappings.telemetry] → 只读、可选（无绑定空列表），既有对象图渲染不变。

## Open Questions

- log 序列的 params 输入 UI 是否本期做？倾向否，先 metric 一键；log 显示模板/提示，params 输入留扩展。
