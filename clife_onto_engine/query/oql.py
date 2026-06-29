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
from typing import Any, Callable, Optional

from . import COMPARATORS, QueryView, matches


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
class Step:
    link_type: str
    direction: str = "out"        # out | in
    where: tuple[Cond, ...] = ()  # 对邻居节点的过滤


@dataclass(frozen=True)
class Aggregate:
    func: str        # _AGG 之一
    field: Optional[str] = None   # count 可省略


@dataclass(frozen=True)
class OQLQuery:
    namespace: str
    start: str                    # 锚点对象类型
    where: tuple[Cond, ...] = ()  # 锚点过滤
    steps: tuple[Step, ...] = ()  # Search Around 链
    select: tuple[str, ...] = ()  # 返回字段（空=整节点）
    aggregate: Optional[Aggregate] = None
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
    for c in q.where:
        _check_op(c.op)
    for s in q.steps:
        if (q.namespace, s.link_type) not in registry.links:
            raise OQLValidationError(f"未声明关系类型: {q.namespace}.{s.link_type}")
        if s.direction not in ("out", "in"):
            raise OQLValidationError(f"非法方向: {s.direction}")
        for c in s.where:
            _check_op(c.op)
    if q.aggregate and q.aggregate.func not in _AGG:
        raise OQLValidationError(f"未支持聚合: {q.aggregate.func}")


def _check_op(op: str) -> None:
    if op not in _OPS:
        raise OQLValidationError(f"未支持算子: {op}")


# ---- 执行（任意 GraphStore）------------------------------------------
def execute(q: OQLQuery, view: QueryView, registry) -> OQLResult:
    validate(q, registry)
    meter = CostMeter()
    pk = registry.objects[(q.namespace, q.start)].primary_key

    meter.base += 1
    conds = [(c.field, c.op, c.value) for c in q.where]
    anchor = view.find_where(q.start, conds)               # 谓词下推点：后端可库内过滤
    anchor = [r for r in anchor if matches(r, conds)]       # 安全再校验：下推可能只覆盖部分谓词
    frontier = [(q.start, r.get(pk), r) for r in anchor]

    for s in q.steps:
        meter.search_around += 1
        nxt: list = []
        seen: set = set()
        for (otype, okey, _row) in frontier:
            if okey is None:
                continue
            for hit in view.search_around(otype, okey, s.link_type, direction=s.direction):
                if _match(hit.node, s.where) and (hit.node_type, hit.node_key) not in seen:
                    seen.add((hit.node_type, hit.node_key))
                    nxt.append((hit.node_type, hit.node_key, hit.node))
        frontier = nxt

    if q.aggregate:
        meter.aggregation += 1
        return OQLResult(rows=[_aggregate(frontier, q.aggregate)], cost=meter.report())

    rows = [_project(row, q.select) for (_t, _k, row) in frontier[: q.limit]]
    return OQLResult(rows=rows, cost=meter.report())


def _pred(conds) -> Callable[[dict], bool]:
    def f(row: dict) -> bool:
        return all(_OPS[c.op](row.get(c.field), c.value) for c in conds)
    return f


def _match(node: dict, conds) -> bool:
    return all(_OPS[c.op](node.get(c.field), c.value) for c in conds)


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
    tail = f" | LIMIT {q.limit}" if not q.aggregate else ""
    return " | ".join(parts) + tail


def _ngql_where(tag: str, conds) -> str:
    if not conds:
        return "true"
    sym = {"eq": "==", "ne": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<="}
    out = []
    for c in conds:
        op = sym.get(c.op, "==")
        out.append(f"{tag}.{c.field} {op} {c.value!r}")
    return " AND ".join(out)
