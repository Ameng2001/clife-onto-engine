"""OQL 功能补全：OR / 嵌套布尔 / order-by —— 执行、校验、解析、nGQL、向后兼容。"""
from __future__ import annotations

import pytest

from clife_onto_engine.intent.compiler import _parse_oql
from clife_onto_engine.query import InMemoryStore, QueryView
from clife_onto_engine.query.oql import (
    And, Cond, OQLQuery, OQLValidationError, Or, Sort, execute, to_ngql, validate,
)
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401

NS = "grass"


def _store():
    s = InMemoryStore()
    rows = [
        ("p1", "巴彦淖尔", "盐碱", 500),
        ("p2", "乌兰察布", "盐碱", 300),
        ("p3", "锡林郭勒", "草原", 800),
        ("p4", "巴彦淖尔", "沙地", 120),
    ]
    for pid, region, st, area in rows:
        s.put_object("Site", pid, {"parcel_id": pid, "region": region, "site_type": st, "area_mu": area})
    return s


def _run(q):
    return execute(q, QueryView(_store(), []), spi.registry).rows


def test_or_group():
    # region ∈ {巴彦淖尔, 乌兰察布}
    q = OQLQuery(namespace=NS, start="Site",
                 where=(Or((Cond("region", "eq", "巴彦淖尔"), Cond("region", "eq", "乌兰察布"))),))
    regions = {r["region"] for r in _run(q)}
    assert regions == {"巴彦淖尔", "乌兰察布"}
    assert len(_run(q)) == 3


def test_nested_and_or():
    # site_type=盐碱 AND (region=巴彦淖尔 OR region=锡林郭勒) → 只 p1
    q = OQLQuery(namespace=NS, start="Site", where=(
        Cond("site_type", "eq", "盐碱"),
        Or((Cond("region", "eq", "巴彦淖尔"), Cond("region", "eq", "锡林郭勒"))),
    ))
    rows = _run(q)
    assert [r["parcel_id"] for r in rows] == ["p1"]


def test_backward_compat_plain_and():
    # 旧语义：Cond tuple = AND，未受影响
    q = OQLQuery(namespace=NS, start="Site",
                 where=(Cond("region", "eq", "巴彦淖尔"), Cond("site_type", "eq", "盐碱")))
    assert [r["parcel_id"] for r in _run(q)] == ["p1"]


def test_order_by_asc_desc_and_multikey():
    q_desc = OQLQuery(namespace=NS, start="Site", order_by=(Sort("area_mu", desc=True),))
    areas = [r["area_mu"] for r in _run(q_desc)]
    assert areas == sorted(areas, reverse=True)
    # 多键：先 region 升序，再 area_mu 降序
    q_multi = OQLQuery(namespace=NS, start="Site",
                       order_by=(Sort("region"), Sort("area_mu", desc=True)))
    rows = _run(q_multi)
    byn = [r for r in rows if r["region"] == "巴彦淖尔"]
    assert [r["area_mu"] for r in byn] == [500, 120]  # 同区域内降序


def test_order_by_none_last():
    s = _store()
    s.put_object("Site", "p9", {"parcel_id": "p9", "region": "赤峰", "site_type": "草原"})  # area_mu 缺
    q = OQLQuery(namespace=NS, start="Site", order_by=(Sort("area_mu"),))
    rows = execute(q, QueryView(s, []), spi.registry).rows
    assert rows[-1]["parcel_id"] == "p9"  # None 排最后（升序）


def test_validate_rejects_bad_op_in_group():
    q = OQLQuery(namespace=NS, start="Site",
                 where=(Or((Cond("region", "BADOP", "x"),)),))
    with pytest.raises(OQLValidationError):
        validate(q, spi.registry)


def test_parse_oql_or_and_order_by():
    d = {"start": "Site",
         "where": [{"or": [{"field": "region", "op": "eq", "value": "巴彦淖尔"},
                           {"field": "region", "op": "eq", "value": "乌兰察布"}]}],
         "order_by": [{"field": "area_mu", "desc": True}]}
    q = _parse_oql(d, NS)
    assert isinstance(q.where[0], Or) and len(q.where[0].any_of) == 2
    assert q.order_by[0].field == "area_mu" and q.order_by[0].desc is True
    # 端到端：解析出的 OQL 可执行
    regions = {r["region"] for r in _run(q)}
    assert regions == {"巴彦淖尔", "乌兰察布"}


def test_to_ngql_renders_or_group_and_order():
    q = OQLQuery(namespace=NS, start="Site",
                 where=(Cond("site_type", "eq", "盐碱"),
                        Or((Cond("region", "eq", "巴彦淖尔"), Cond("region", "eq", "乌兰察布")))),
                 order_by=(Sort("area_mu", desc=True),))
    ngql = to_ngql(q)
    assert "OR" in ngql and "(" in ngql and "ORDER BY" in ngql and "DESC" in ngql
