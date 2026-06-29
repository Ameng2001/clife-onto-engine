"""Action 引擎：commit / guard / 写后规则回滚 / validate 预演 / 审计。"""
from __future__ import annotations

from clife_onto_engine import ActionEngine
from clife_onto_engine.sdk import spi

NS = "grass"


def _engine(store):
    return ActionEngine(spi.registry, store=store)


def test_commit_writes_and_audits(grass_store, contractor):
    eng = _engine(grass_store)
    res = eng.execute(NS, "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅", "披碱草"], "budget": 300},
                      contractor, schema_version="grass@0.1.0", ts="t")
    assert res.committed is True
    assert grass_store.get_object("SeedPack", "sp_parcel_001") is not None
    audits = eng.audit.query(NS)
    assert len(audits) == 1 and audits[0].decision == "committed"


def test_post_rule_rejection_rolls_back(grass_store, contractor):
    eng = _engine(grass_store)
    res = eng.execute(NS, "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅", "紫花苜蓿"], "budget": 300},
                      contractor, schema_version="grass@0.1.0", ts="t")
    assert res.committed is False
    assert res.phase == "post_write"
    assert [v.rule for v in res.violations] == ["乡土合规"]
    # 回滚：图库零写入
    assert grass_store.get_object("SeedPack", "sp_parcel_001") is None


def test_guard_blocks_negative_budget(grass_store, contractor):
    eng = _engine(grass_store)
    res = eng.execute(NS, "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅"], "budget": -5},
                      contractor, ts="t")
    assert res.committed is False and res.phase == "guard"


def test_validate_preview_no_side_effect(grass_store, contractor):
    eng = _engine(grass_store)
    prev = eng.validate(NS, "出一地一方",
                        {"site_id": "parcel_001", "species": ["碱茅"], "budget": 100}, contractor)
    assert prev.would_commit is True
    assert grass_store.get_object("SeedPack", "sp_parcel_001") is None  # 预演不落库


def test_multi_rule_collects_all_not_short_circuit(grass_store, contractor):
    # 快检评级缺检测项 → guard 收集；这里验证写后多违反不短路用乡土+另一条不易构造，
    # 改测 guard 同时多违反：角色不符 + 预算负
    eng = _engine(grass_store)
    from clife_onto_engine.sdk.context import Actor
    res = eng.execute(NS, "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅"], "budget": -1},
                      Actor("x", "陌生人"), ts="t")
    assert res.committed is False
    rules = {v.rule for v in res.violations}
    assert "预算非负" in rules and "角色权限" in rules  # 收集全部
