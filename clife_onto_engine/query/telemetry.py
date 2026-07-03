"""遥测 query-plan 生成 —— 本体 OS 自有"深读"的遥测侧（与 OQL 对象图读互补）。

据对象实例 + 声明的遥测绑定，把实例的 label 值**安全代入**生成器模板，产出**可执行查询计划**
（PromQL / ES DSL / SQL，id 已代入）。引擎**只产计划、不连后端、不执行**——与 UModel 同立场，
调用方（skill/agent/HTTP）拿计划自行打后端。天然离线、可测。

与 OQL 同纪律：不裸拼查询串——label 值先白名单校验（防注入），越界即拒。
与行业无关（CI 强制）：本模块只读绑定/实例，不含任何行业词汇。
"""
from __future__ import annotations

import re

# label 值白名单：字母数字 + 常见安全符（-_.:/ 空格中文）；元字符（{}"'`\等）一律拒，防注入。
_SAFE_LABEL = re.compile(r"^[\w\-.:/ 一-鿿]+$")
# 标识符白名单（表/列/维度名）：ASCII/中文标识符，防手误注入（来自声明的绑定，受信但仍校验）。
_SAFE_IDENT = re.compile(r"^[A-Za-z_一-鿿][\w一-鿿]*$")
_ANALYTIC_AGG = {"avg", "sum", "min", "max", "count"}


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


def build_analytical_plan(registry, namespace: str, metric_name: str,
                          *, params: dict | None = None) -> dict:
    """语义指标（Profile B）→ 数仓 SQL 查询计划（不执行；DuckDB/ClickHouse 等执行器跑）。

    度量/维度/来源来自声明（受信，仍走标识符白名单）；过滤 `$占位` 值由 params 代入并
    走 label 白名单**防注入**。成功 → {ok, provider, kind:'analytical', plan, dimensions, ...}。
    与 build_plan（Profile A·单序列）分工：本函数产**维度化聚合**查询（分析读·虚拟递数仓）。
    """
    m = registry.mappings.get_analytics(namespace, metric_name)
    if m is None:
        return _err(f"未声明语义指标: {namespace}.{metric_name}")
    if m.agg not in _ANALYTIC_AGG:
        return _err(f"未支持聚合: {m.agg}")
    idents = [m.source] + ([m.metric_field] if m.metric_field else []) + list(m.dimensions) + list(m.filters)
    for ident in idents:
        if not _SAFE_IDENT.match(ident):
            return _err(f"非法标识符（防注入）: {ident!r}")
    measure = "count(*)" if m.agg == "count" else f"{m.agg}({m.metric_field})"
    alias = m.metric_field or "count"
    dims = ", ".join(m.dimensions)
    select = (dims + ", " if dims else "") + f"{measure} AS {alias}"

    params = params or {}
    where, resolved = [], {}
    for col, val in m.filters.items():
        v = val
        if isinstance(val, str) and val.startswith("$"):
            ph = val[1:]
            if ph not in params:
                return _err(f"未解析过滤占位 '${ph}'（未在 params 给出）")
            v = params[ph]
        if not _SAFE_LABEL.match(str(v)):
            return _err(f"过滤值含非法字符，拒绝代入（防注入）: {col}={v!r}")
        where.append(f"{col} = '{v}'")
        resolved[col] = str(v)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    group = (" GROUP BY " + dims) if dims else ""
    order = (" ORDER BY " + dims) if dims else ""
    plan = f"SELECT {select} FROM {m.source}{clause}{group}{order}"
    return {"ok": True, "provider": m.provider, "kind": "analytical", "plan": plan,
            "metric": metric_name, "dimensions": list(m.dimensions),
            "resolved_filters": resolved, "cost": {"analytical-plan": 1}}


def build_plan(registry, store, object_type: str, key: str, series_name: str,
               *, namespace: str, params: dict | None = None) -> dict:
    """生成可执行查询计划（不执行）。

    占位两段解析：对象 label（从实例代入）先，模板剩余 `$占位` 由运行时 `params` 解析
    （典型用于 log 的 level/时间窗）。两者同白名单防注入；仍有未解析占位即拒。

    成功 → {ok, provider, kind, plan, resolved_labels, resolved_params, cost}；失败 → {ok: False, error}。
    """
    binding = registry.mappings.get_telemetry(namespace, object_type)
    if binding is None:
        return _err(f"未声明遥测绑定: {namespace}.{object_type}")
    series = next((s for s in binding.series if s.name == series_name), None)
    if series is None:
        avail = [s.name for s in binding.series]
        return _err(f"绑定无序列 '{series_name}'，可用: {avail}")
    row = store.get_object(object_type, key)
    if row is None:
        return _err(f"对象实例不存在: {object_type}/{key}")

    resolved: dict[str, str] = {}
    plan = series.template
    # 第一段：对象 label（治理数据）从实例代入
    for placeholder, field in binding.labels.items():
        if field not in row or row[field] is None:
            return _err(f"实例缺 label 字段 '{field}'（占位 ${placeholder}）")
        val = str(row[field])
        if not _SAFE_LABEL.match(val):
            return _err(f"label 值含非法字符，拒绝代入（防注入）: {placeholder}={val!r}")
        resolved[placeholder] = val
        plan = plan.replace(f"${placeholder}", val)

    # 第二段：模板剩余 $占位 由运行时 params 解析（log 过滤等）
    params = params or {}
    resolved_params: dict[str, str] = {}
    for placeholder in sorted(set(re.findall(r"\$(\w+)", plan))):
        if placeholder not in params:
            return _err(f"未解析占位 '${placeholder}'（既非对象 label 又未在 params 给出）")
        val = str(params[placeholder])
        if not _SAFE_LABEL.match(val):
            return _err(f"params 值含非法字符，拒绝代入（防注入）: {placeholder}={val!r}")
        resolved_params[placeholder] = val
        plan = plan.replace(f"${placeholder}", val)

    return {"ok": True, "provider": series.provider, "kind": series.kind,
            "plan": plan, "object": object_type, "key": key, "series": series_name,
            "resolved_labels": resolved, "resolved_params": resolved_params,
            "cost": {"telemetry-plan": 1}}


# ---- 执行器（可选）：完成"看指标"回路 —— 引擎产计划，执行器出值 --------------
# 与 build_plan 分层：引擎只产计划（不连后端）；执行器是调用方侧组件。
# 离线默认 InMemoryTelemetryExecutor 读 seeded 值/序列、不解析 PromQL，脱网可跑、可 CI 测；
# 真部署换成打 Prometheus/ES/SQL 的适配器（同协议、同 plan 契约）。行业无关。
from typing import Protocol  # noqa: E402


class TelemetryExecutor(Protocol):
    """执行遥测计划、返回值/序列。接收 build_plan 的 plan dict。"""
    def execute(self, plan: dict) -> dict: ...


class InMemoryTelemetryExecutor:
    """离线确定性执行器：按 (object_type, series, key) 查 seeded 值/序列。

    不解析 plan 里的 PromQL/ES 串——那是真后端的活；离线默认据对象定位直接取 seeded 数据，
    让 `ask("这块地墒情多少")` 端到端出值。metric→标量 value；log→points 列表。
    """

    def __init__(self, data: dict | None = None) -> None:
        self._data = dict(data or {})  # {(object_type, series_name, key): 标量 | 列表}

    def put(self, object_type: str, series_name: str, key: str, value) -> None:
        self._data[(object_type, series_name, key)] = value

    def execute(self, plan: dict) -> dict:
        if not plan.get("ok"):
            return plan
        k = (plan.get("object"), plan.get("series"), plan.get("key"))
        if k not in self._data:
            return _err(f"离线遥测无数据: {k}")
        val = self._data[k]
        out = {"ok": True, "provider": plan["provider"], "kind": plan["kind"], "plan": plan["plan"]}
        if plan["kind"] == "log":
            out["points"] = list(val)
        else:
            out["value"] = val
        return out
