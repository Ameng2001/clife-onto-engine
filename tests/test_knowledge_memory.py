"""附着知识喂进 Memory：装载、相关性注入、Session 集成、kinds 过滤、默认关兼容。"""
from __future__ import annotations

from clife_onto_engine.knowledge import load_into_memory
from clife_onto_engine.memory import Layer, MemoryStore, assemble
from clife_onto_engine.memory.retrieval import relevance
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


def test_loads_knowledge_as_background():
    mem = MemoryStore()
    n = load_into_memory(spi.registry, mem, "grass", "s1")
    assert n >= 4
    bg = mem.by_layer(Layer.BACKGROUND, "grass", "s1")
    assert bg and all(it.source == "knowledge" for it in bg)
    assert any("盐碱化" in it.content for it in bg)


def test_relevant_knowledge_assembled():
    mem = MemoryStore()
    load_into_memory(spi.registry, mem, "grass", "s1")
    ctx = assemble(mem, "grass", "s1", {"退化", "盐碱化", "修复"})
    assert "盐碱化" in ctx.text or "退化分级" in ctx.text     # 相关知识进上下文（喂 LLM）


def test_relevance_ranks_related_higher():
    mem = MemoryStore()
    load_into_memory(spi.registry, mem, "grass", "s1")
    deg = next(it for it in mem.by_layer(Layer.BACKGROUND, "grass", "s1") if "盐碱化" in it.content)
    assert relevance(deg, {"退化", "盐碱化"}) > relevance(deg, {"无关词"})


def test_kinds_filter():
    mem = MemoryStore()
    n = load_into_memory(spi.registry, mem, "grass", "s1", kinds={"template"})
    bg = mem.by_layer(Layer.BACKGROUND, "grass", "s1")
    assert n == len(bg) and all("template" in it.tags for it in bg)


class _NoCompiler:
    pass


def test_session_load_knowledge_opt_in():
    from clife_onto_engine.query import InMemoryStore
    store = InMemoryStore(); plugins.grass.seed_reference_data(store)
    from clife_onto_engine.session import Session
    s_on = Session(ontology_id="grass", registry=spi.registry, store=store,
                   compiler=_NoCompiler(), actor=Actor("u", "施工方"),
                   session_id="k1", load_knowledge=True)
    assert s_on.memory.by_layer(Layer.BACKGROUND, "grass", "k1")     # 装载了
    s_off = Session(ontology_id="grass", registry=spi.registry, store=store,
                    compiler=_NoCompiler(), actor=Actor("u", "施工方"), session_id="k2")
    assert not s_off.memory.by_layer(Layer.BACKGROUND, "grass", "k2")  # 默认不装载
