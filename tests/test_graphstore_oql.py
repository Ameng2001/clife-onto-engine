"""GraphStore SPI（Search Around / overlay 写即可见 / find_where）与 OQL。"""
from __future__ import annotations

import pytest

from clife_onto_engine.query import InMemoryStore, QueryView, StagedLink
from clife_onto_engine.query.oql import (
    Aggregate,
    Cond,
    OQLQuery,
    OQLValidationError,
    Step,
    execute,
    validate,
)
from clife_onto_engine.sdk import spi

NS = "grass"


def test_search_around_both_directions(grass_store):
    out = grass_store.search_around("Degradation", "deg1", "treated_by")
    assert {h.node_key for h in out} == {"m1", "m2"}
    rev = grass_store.search_around("RestorationMethod", "m1", "treated_by", direction="in")
    assert [h.node_key for h in rev] == ["deg1"]


def test_overlay_write_immediately_visible(grass_store):
    overlay: list = []
    view = QueryView(grass_store, overlay)
    overlay.append(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m3"))
    grass_store.put_object("RestorationMethod", "m3", {"method_id": "m3", "name": "封禁"})
    seen = {h.node_key for h in view.search_around("Degradation", "deg1", "treated_by")}
    assert "m3" in seen                                    # 暂存边可见
    base = {h.node_key for h in grass_store.search_around("Degradation", "deg1", "treated_by")}
    assert "m3" not in base                                # 未落库


def test_oql_multihop(grass_store):
    q = OQLQuery(namespace=NS, start="Site", where=(Cond("parcel_id", "eq", "parcel_001"),),
                 steps=(Step("suffers"), Step("treated_by")), select=("name",))
    r = execute(q, QueryView(grass_store, []), spi.registry)
    assert sorted(x["name"] for x in r.rows) == ["喷播", "补播"]
    assert r.cost["search_around"] == 2


def test_oql_aggregate(grass_store):
    q = OQLQuery(namespace=NS, start="Site", where=(Cond("region", "eq", "巴彦淖尔"),),
                 aggregate=Aggregate("count"))
    r = execute(q, QueryView(grass_store, []), spi.registry)
    assert r.rows == [{"count": 1}]


def test_oql_injection_rejected():
    bad = OQLQuery(namespace=NS, start="Site", steps=(Step("DROP_ALL"),))
    with pytest.raises(OQLValidationError):
        validate(bad, spi.registry)


def test_find_where_pushdown_inmemory(grass_store):
    rows = grass_store.find_where("Site", [("region", "eq", "巴彦淖尔")])
    assert {r["parcel_id"] for r in rows} == {"parcel_001"}
