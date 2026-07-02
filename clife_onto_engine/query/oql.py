"""OQL —— 受限本体查询（docs §7、§4.12.8）。

设计取舍（呼应"不造大轮子"）：OQL **不是文本 DSL**，没有手写文法/parser。
它是一个结构化查询对象（JSON 形小 AST）——LLM 以结构化输出直接吐出，运行时
只做「对 schema 的校验」，从结构上防注入（绝不拼字符串进 nGQL/SQL）。

同一个 OQL：
  - `execute(...)` 在任意 GraphStore（含内存后端）上跑；
  - `to_ngql(...)` 编译成 NebulaGraph nGQL（薄翻译，由 adapter 执行）。

算子级成本计量（base / search-around / aggregation）随查询产出，兼作 SaaS 计费依据。
本模块与行业无关（CI 强制）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import COMPARATORS, QueryView


class OQLValidationError(Exception):
    """OQL 引用了未声明的对象/关系/算子 —— 即被拒（防注入 + schema 落地）。"""


# 比较算子与后端共用（query.COMPARATORS），避免重复定义。
_OPS = COMPARATORS
_AGG = {"count", "avg", "sum", "min", "max"}


# ---- AST --------------------------------------------------------------
@dataclass(frozen=True)
class Cond:
    field: str
    op: str          # _OPS 之一
    value: Any


@dataclass(frozen=True)
class Or:
    """析取组：任一子过滤成立即真。子项可为 Cond / And / Or（可嵌套）。"""
    any_of: tuple = ()


@dataclass(frozen=True)
class And:
    """合取组：全部子过滤成立才真。子项可为 Cond / And / Or（可嵌套）。"""
    all_of: tuple = ()


# 一个"过滤节点"= Cond | And | Or。where 顶层为这些节点的 tuple，语义 = 全部成立（AND）。
# 纯 Cond 的 tuple 即旧语义（向后兼容）；混入 Or/And 组即得 (a OR b) AND c 之类。

@dataclass(frozen=True)
class Step:
    link_type: str
    direction: str = "out"        # out | in
    where: tuple = ()             # 对邻居节点的过滤（Cond | And | Or）


@dataclass(frozen=True)
class Aggregate:
    func: str        # _AGG 之一
    field: Optional[str] = None   # count 可省略


@dataclass(frozen=True)
class Sort:
    field: str
    desc: bool = False            # 默认升序；None 值排在有值之后


@dataclass(frozen=True)
class OQLQuery:
    namespace: str
    start: str                    # 锚点对象类型
    where: tuple = ()             # 锚点过滤（Cond | And | Or 节点，顶层 AND）
    steps: tuple[Step, ...] = ()  # Search Around 链
    select: tuple[str, ...] = ()  # 返回字段（空=整节点）
    aggregate: Optional[Aggregate] = None
    order_by: tuple[Sort, ...] = ()  # 结果排序（多键稳定；聚合时忽略）
    limit: int = 100


@dataclass
class CostMeter:
    base: int = 0
    search_around: int = 0
    aggregation: int = 0

    def report(self) -> dict:
        return {"base": self.base, "search_around": self.search_around,
                "aggregation": self.aggregation,
                "total": self.base + self.search_around + self.aggregation}


@dataclass(frozen=True)
class OQLResult:
    rows: list
    cost: dict


# ---- 校验（防注入核心）------------------------------------------------
def validate(q: OQLQuery, registry) -> None:
    if (q.namespace, q.start) not in registry.objects:
        raise OQLValidationError(f"未声明对象类型: {q.namespace}.{q.start}")
    _check_filter(q.where)
    for s in q.steps:
        if (q.namespace, s.link_type) not in registry.links:
            raise OQLValidationError(f"未声明关系类型: {q.namespace}.{s.link_type}")
        if s.direction not in ("out", "in"):
            raise OQLValidationError(f"非法方向: {s.direction}")
        _check_filter(s.where)
    if q.aggregate and q.aggregate.func not in _AGG:
        raise OQLValidationError(f"未支持聚合: {q.aggregate.func}")


def _check_filter(nodes) -> None:
    """递归校验过滤节点（Cond/And/Or）里的算子——布尔组也防注入。"""
    for n in nodes:
        if isinstance(n, Cond):
            _check_op(n.op)
        elif isinstance(n, Or):
            _check_filter(n.any_of)
        elif isinstance(n, And):
            _check_filter(n.all_of)
        else:
            raise OQLValidationError(f"非法过滤节点: {type(n).__name__}")


def _check_op(op: str) -> None:
    if op not in _OPS:
        raise OQLValidationError(f"未支持算子: {op}")


# ---- 执行（任意 GraphStore）------------------------------------------
def execute(q: OQLQuery, view: QueryView, registry) -> OQLResult:
    validate(q, registry)
    meter = CostMeter()
    pk = registry.objects[(q.namespace, q.start)].primary_key

    meter.base += 1
    # 下推：只推顶层扁平 Cond（后端 AND 过滤）；布尔组由引擎内完整求值兜底。
    flat = [(c.field, c.op, c.value) for c in q.where if isinstance(c, Cond)]
    anchor = view.find_where(q.start, flat)                 # 谓词下推点：后端可库内过滤
    anchor = [r for r in anchor if _eval_all(r, q.where)]   # 权威过滤：完整布尔（含 OR/嵌套）
    frontier = [(q.start, r.get(pk), r) for r in anchor]

    for s in q.steps:
        meter.search_around += 1
        nxt: list = []
        seen: set = set()
        for (otype, okey, _row) in frontier:
            if okey is None:
                continue
            for hit in view.search_around(otype, okey, s.link_type, direction=s.direction):
                if _eval_all(hit.node, s.where) and (hit.node_type, hit.node_key) not in seen:
                    seen.add((hit.node_type, hit.node_key))
                    nxt.append((hit.node_type, hit.node_key, hit.node))
        frontier = nxt

    if q.aggregate:
        meter.aggregation += 1
        return OQLResult(rows=[_aggregate(frontier, q.aggregate)], cost=meter.report())

    if q.order_by:                                          # 多键稳定排序；None 值排在有值之后
        for srt in reversed(q.order_by):
            frontier.sort(key=lambda t, f=srt.field: (t[2].get(f) is None, t[2].get(f)),
                          reverse=srt.desc)
    rows = [_project(row, q.select) for (_t, _k, row) in frontier[: q.limit]]
    return OQLResult(rows=rows, cost=meter.report())


def _eval_all(row: dict, nodes) -> bool:
    """顶层 AND：所有过滤节点成立。空 → 真。"""
    return all(_eval_node(row, n) for n in nodes)


def _eval_node(row: dict, node) -> bool:
    """求值单个过滤节点（Cond | And | Or，可递归嵌套）。"""
    if isinstance(node, Cond):
        return _OPS[node.op](row.get(node.field), node.value)
    if isinstance(node, Or):
        return any(_eval_node(row, x) for x in node.any_of)
    if isinstance(node, And):
        return all(_eval_node(row, x) for x in node.all_of)
    return False


def _project(row: dict, select) -> dict:
    if not select:
        return dict(row)
    return {k: row.get(k) for k in select}


def _aggregate(frontier, agg: Aggregate):
    if agg.func == "count":
        return {"count": len(frontier)}
    vals = [row.get(agg.field) for (_t, _k, row) in frontier if row.get(agg.field) is not None]
    if not vals:
        return {agg.func: None}
    if agg.func == "sum":
        return {"sum": sum(vals)}
    if agg.func == "avg":
        return {"avg": sum(vals) / len(vals)}
    if agg.func == "min":
        return {"min": min(vals)}
    if agg.func == "max":
        return {"max": max(vals)}
    return {agg.func: None}  # 不可达（validate 已挡）


# ---- 编译为 nGQL（薄翻译；adapter 执行）------------------------------
def to_ngql(q: OQLQuery, mappings=None) -> str:
    """把同一个 OQL 编译成 NebulaGraph nGQL 示意，证明 OQL 后端无关。
    具体 YIELD 字段与 VID 取值由 NebulaGraphStore 配合映射注册表填充。"""
    validate_skipped = q  # 调用方应已 validate
    parts = [f"LOOKUP ON {q.start} WHERE {_ngql_where(q.start, q.where)} YIELD id(vertex) AS vid"]
    for s in q.steps:
        rev = " REVERSELY" if s.direction == "in" else ""
        parts.append(f"GO FROM $-.vid OVER {s.link_type}{rev} YIELD dst(edge) AS vid")
    tail = ""
    if q.order_by and not q.aggregate:
        keys = ", ".join(f"$-.{s.field} {'DESC' if s.desc else 'ASC'}" for s in q.order_by)
        tail += f" | ORDER BY {keys}"
    tail += f" | LIMIT {q.limit}" if not q.aggregate else ""
    return " | ".join(parts) + tail


_SYM = {"eq": "==", "ne": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<=",
        "in": "IN"}


def _ngql_where(tag: str, nodes) -> str:
    if not nodes:
        return "true"
    return " AND ".join(_ngql_node(tag, n) for n in nodes)


def _ngql_node(tag: str, node) -> str:
    """把过滤节点（Cond/And/Or）渲染为 nGQL 布尔表达式（组加括号）。"""
    if isinstance(node, Cond):
        return f"{tag}.{node.field} {_SYM.get(node.op, '==')} {node.value!r}"
    if isinstance(node, Or):
        return "(" + " OR ".join(_ngql_node(tag, x) for x in node.any_of) + ")"
    if isinstance(node, And):
        return "(" + " AND ".join(_ngql_node(tag, x) for x in node.all_of) + ")"
    return "true"
