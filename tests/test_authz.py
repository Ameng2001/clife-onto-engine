"""声明式授权：策略判定 + 引擎前置门（越权无副作用+审计、授权正常、validate、向后兼容、YAML）。"""
from __future__ import annotations

from clife_onto_engine.authz import AuthzPolicy
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401


def _seeded():
    s = InMemoryStore(); plugins.grass.seed_reference_data(s); return s


def _policy():
    return AuthzPolicy(default_allow=False).grant("grass", "出一地一方", "施工方")


P = {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300}


def test_policy_grant_and_default_deny():
    p = _policy()
    assert p.allows("grass", "出一地一方", "施工方")
    assert not p.allows("grass", "出一地一方", "游客")
    assert not p.allows("grass", "未声明动作", "施工方")  # default-deny


def test_unauthorized_blocked_before_any_write():
    store = _seeded()
    eng = ActionEngine(spi.registry, store=store, authz=_policy())
    res = eng.execute("grass", "出一地一方", P, Actor("g", "游客"), schema_version="v")
    assert not res.committed and res.phase == "authz"
    assert store.get_object("Project", "proj_parcel_001") is None       # 无副作用
    assert eng.audit.query("grass")[-1].decision == "unauthorized"      # 审计留痕


def test_authorized_proceeds():
    eng = ActionEngine(spi.registry, store=_seeded(), authz=_policy())
    res = eng.execute("grass", "出一地一方", P, Actor("u1", "施工方"), schema_version="v")
    assert res.committed


def test_validate_enforces_authz():
    eng = ActionEngine(spi.registry, store=_seeded(), authz=_policy())
    prev = eng.validate("grass", "出一地一方", P, Actor("g", "游客"))
    assert not prev.would_commit and any(v.rule == "authz" for v in prev.violations)


def test_no_authz_backward_compatible():
    # 无 authz：游客被插件业务 guard「角色权限」拦（phase=guard），不是 authz
    eng = ActionEngine(spi.registry, store=_seeded())
    res = eng.execute("grass", "出一地一方", P, Actor("g", "游客"), schema_version="v")
    assert not res.committed and res.phase == "guard"


def test_yaml_load(tmp_path):
    y = tmp_path / "authz.yaml"
    y.write_text("default_allow: false\ngrants:\n  - action: 出一地一方\n    roles: [施工方, 监管]\n",
                 encoding="utf-8")
    p = AuthzPolicy().load_yaml("grass", str(y))
    assert p.allows("grass", "出一地一方", "监管") and not p.allows("grass", "出一地一方", "游客")
