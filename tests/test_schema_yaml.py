"""YAML Schema 加载器：声明式对象/关系 schema → registry（Python add_* 的同构落点）→ OQL 可查。"""
from __future__ import annotations

import pytest

from clife_onto_engine.metamodel import EdgeSemantics
from clife_onto_engine.query import InMemoryStore, QueryView
from clife_onto_engine.query.oql import Cond, OQLQuery, execute
from clife_onto_engine.sdk.errors import RegistrationError
from clife_onto_engine.sdk.registry import SPI

_SCHEMA = """
objects:
  - name: Widget
    primary_key: wid
    states: [draft, active]
    initial_state: draft
    properties:
      - {name: size, type: number, unit: cm, required: true}
      - {name: label, type: string}
  - name: Gadget
    primary_key: gid
links:
  - name: uses_widget
    from: Gadget
    to: Widget
    edge_semantics: hypothesis
"""


def _write(tmp_path, text=_SCHEMA):
    p = tmp_path / "schema.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_schema_registers_objects_links(tmp_path):
    spi = SPI()  # 独立 registry
    n_obj, n_link = spi.load_schema("demo", _write(tmp_path))
    assert (n_obj, n_link) == (2, 1)
    w = spi.registry.objects[("demo", "Widget")]
    assert w.primary_key == "wid" and w.states == ("draft", "active") and w.initial_state == "draft"
    props = {p.name: p for p in w.properties}
    assert props["size"].type == "number" and props["size"].required and props["size"].unit == "cm"
    assert not props["label"].required
    lk = spi.registry.links[("demo", "uses_widget")]
    assert lk.from_type == "Gadget" and lk.to_type == "Widget"
    assert lk.edge_semantics == EdgeSemantics.HYPOTHESIS       # 显式声明的语义


def test_default_edge_semantics_is_derivation(tmp_path):
    spi = SPI()
    spi.load_schema("demo", _write(tmp_path, "links:\n  - {name: r, from: A, to: B}\n"
                                             "objects:\n  - {name: A, primary_key: a}\n"
                                             "  - {name: B, primary_key: b}\n"))
    assert spi.registry.links[("demo", "r")].edge_semantics == EdgeSemantics.DERIVATION


def test_yaml_schema_is_oql_queryable(tmp_path):
    spi = SPI()
    spi.load_schema("demo", _write(tmp_path))
    store = InMemoryStore()
    store.put_object("Widget", "w1", {"wid": "w1", "size": 5, "label": "a"})
    store.put_object("Widget", "w2", {"wid": "w2", "size": 1})
    rows = execute(OQLQuery(namespace="demo", start="Widget", where=(Cond("size", "ge", 3),)),
                   QueryView(store, []), spi.registry).rows
    assert [r["wid"] for r in rows] == ["w1"]                  # YAML 声明的 schema 上跑 OQL


def test_duplicate_declaration_guarded(tmp_path):
    spi = SPI()
    spi.load_schema("demo", _write(tmp_path))
    with pytest.raises(RegistrationError):                     # 重复声明被 _guard_dup 拦
        spi.load_schema("demo", _write(tmp_path))
