"""to_ngql 真翻译：原生列门控下推 / 主键→id(vertex) / 布尔括号 / IN / 多跳 / count / 排序 / 兼容。

结构断言（复用 nebula_store 已验证的 LOOKUP/GO/YIELD/字面量形态）；执行等价性由 opt-in
scripts/nebula_to_ngql.py 在真集群对齐 execute() 交叉验证。
"""
from __future__ import annotations

from clife_onto_engine.query.oql import Aggregate, Cond, OQLQuery, Or, Sort, Step, to_ngql
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401

R = spi.registry


def ng(q):
    return to_ngql(q, R)


def test_anchor_yields_props_and_limit():
    s = ng(OQLQuery(namespace="grass", start="Site"))
    assert "LOOKUP ON Site" in s and "properties(vertex).props AS props" in s and "| LIMIT 100" in s


def test_native_where_pushed_double_quoted():
    s = ng(OQLQuery(namespace="grass", start="Site", where=(Cond("region", "eq", "巴彦淖尔"),)))
    assert 'WHERE Site.region == "巴彦淖尔"' in s        # region 是原生列；双引号（同 _lit）


def test_primary_key_maps_to_id_vertex():
    s = ng(OQLQuery(namespace="grass", start="Site", where=(Cond("parcel_id", "eq", "p1"),)))
    assert 'id(vertex) == "p1"' in s and "Site.parcel_id" not in s


def test_or_group_parenthesized():
    s = ng(OQLQuery(namespace="grass", start="Site",
                    where=(Or((Cond("region", "eq", "A"), Cond("region", "eq", "B"))),)))
    assert '(Site.region == "A" OR Site.region == "B")' in s


def test_in_list_rendering():
    s = ng(OQLQuery(namespace="grass", start="Site", where=(Cond("region", "in", ["A", "B"]),)))
    assert 'Site.region IN ["A", "B"]' in s


def test_non_native_field_falls_back_to_full_scan():
    # Degradation 无映射 → 原生列空 → 任何 where 不下推（全 LOOKUP，引擎再过滤，正确性不损）
    s = ng(OQLQuery(namespace="grass", start="Degradation", where=(Cond("level", "eq", "重度"),)))
    assert "WHERE" not in s and "LOOKUP ON Degradation" in s


def test_multihop_go_and_orderby_suppressed():
    q = OQLQuery(namespace="grass", start="Site", where=(Cond("parcel_id", "eq", "p1"),),
                 steps=(Step("suffers", "out"), Step("treated_by", "out")),
                 order_by=(Sort("area_mu"),))
    s = ng(q)
    assert "GO FROM $-.vid OVER suffers" in s and "GO FROM $-.vid OVER treated_by" in s
    assert "ORDER BY" not in s                          # 多跳后不下推 order by（props 是 blob）


def test_reversely_for_in_direction():
    assert "REVERSELY" in ng(OQLQuery(namespace="grass", start="Site", steps=(Step("suffers", "in"),)))


def test_count_aggregate_and_no_limit():
    s = ng(OQLQuery(namespace="grass", start="Site", aggregate=Aggregate("count")))
    assert "| YIELD COUNT(*) AS count" in s and "LIMIT" not in s


def test_order_by_native_pushed():
    s = ng(OQLQuery(namespace="grass", start="Site", order_by=(Sort("area_mu", desc=True),)))
    assert "| ORDER BY $-.area_mu DESC" in s


def test_backward_compat_without_registry():
    # 无 registry → best-effort 全下推（供无映射的测试/演示）
    s = to_ngql(OQLQuery(namespace="grass", start="Site", where=(Cond("region", "eq", "A"),)))
    assert 'Site.region == "A"' in s
