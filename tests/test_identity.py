"""身份解析：StaticIdentityResolver 解析/None、Principal.actor。"""
from __future__ import annotations

from clife_onto_engine.identity import Principal, StaticIdentityResolver
from clife_onto_engine.sdk.context import Actor


def test_resolve_valid():
    r = StaticIdentityResolver().add("k1", "A", "u1", "施工方")
    p = r.resolve("k1")
    assert p == Principal("A", "u1", "施工方")
    assert p.actor == Actor("u1", "施工方")


def test_resolve_invalid_none():
    r = StaticIdentityResolver().add("k1", "A", "u1", "施工方")
    assert r.resolve("bad") is None and r.resolve("") is None


def test_ctor_dict():
    r = StaticIdentityResolver({"k": Principal("T", "i", "r")})
    assert r.resolve("k").tenant == "T"
