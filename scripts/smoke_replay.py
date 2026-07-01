"""决策重放 + 本体版本化 smoke（治理化变更生命周期地基）。

证明：真实 execute 落审计 → 取快照重放**复现**裁决；**反事实**（换非乡土草种）翻转；
对**更严版本**（预算门槛提高）重放翻转；版本**不可变**（快照后活 registry 变更不污染）。
全离线、无 LLM。
"""
from __future__ import annotations

import pathlib
import sys
from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.replay import replay
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.versioning import OntologyVersionStore, snapshot_ontology

import plugins.grass  # noqa: F401


def _seeded_store():
    s = InMemoryStore()
    plugins.grass.seed_reference_data(s)  # Site/parcel_001 + 巴彦淖尔乡土名录
    return s


def main() -> int:
    fails = 0
    # 1) 真实 execute（合规草种）→ 落审计
    store = _seeded_store()
    engine = ActionEngine(spi.registry, store=store)
    actor = Actor("u1", "施工方")
    engine.execute("grass", "出一地一方",
                   {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300}, actor,
                   schema_version="grass@0.1.0")
    snap = engine.audit.query("grass")[-1]
    print(f"== 审计快照：{snap.action} · 原裁决={snap.decision} ==")

    # 2) 对活 registry + seeded store 重放 → 复现
    r = replay(snap, spi.registry, store=_seeded_store())
    ok = (not r.flipped) and r.replay_would_commit
    print(f"== 重放复现：{'✓' if ok else '✗'} · {r.summary} ==")
    fails += not ok

    # 3) 反事实：换非乡土草种 → 翻转（乡土合规拦）
    r2 = replay(snap, spi.registry, store=_seeded_store(),
                param_overrides={"species": ["紫花苜蓿"]})
    ok2 = r2.flipped and (not r2.replay_would_commit) and any(v.rule == "乡土合规" for v in r2.violations)
    print(f"== 反事实翻转：{'✓' if ok2 else '✗'} · {r2.summary} ==")
    fails += not ok2

    # 4) 版本敏感：构造"预算门槛≥500"的更严版本 → budget=300 决策翻转
    vstore = OntologyVersionStore()
    v_strict = vstore.snapshot(spi.registry, "grass", "grass@strict")
    orig = v_strict.registry.rules[("grass", "预算非负")]

    def _budget_ge_500(ctx):
        from clife_onto_engine.sdk import RuleResult
        b = ctx.params.get("budget", 0)
        return RuleResult.ok() if (b is not None and b >= 500) else RuleResult.fail("预算需≥500")
    v_strict.registry.rules[("grass", "预算非负")] = replace(orig, impl=_budget_ge_500)

    r3 = replay(snap, v_strict.registry, store=_seeded_store(), against_version="grass@strict")
    ok3 = r3.flipped and (not r3.replay_would_commit)
    print(f"== 换更严版本翻转：{'✓' if ok3 else '✗'} · {r3.summary} ==")
    fails += not ok3

    # 5) 版本不可变：快照后往活 registry 加个动作，旧版本查不到
    v1 = snapshot_ontology(spi.registry, "grass", "grass@0.1.0")
    before = set(v1.registry.actions)
    from clife_onto_engine.metamodel import ActionDef
    spi.registry.actions[("grass", "_tmp_probe")] = ActionDef(name="_tmp_probe", namespace="grass")
    after = set(v1.registry.actions)
    del spi.registry.actions[("grass", "_tmp_probe")]  # 清理
    ok5 = before == after and ("grass", "_tmp_probe") not in v1.registry.actions
    print(f"== 版本不可变：{'✓' if ok5 else '✗'} ==")
    fails += not ok5

    if fails:
        print(f"\n✗ 重放/版本化 smoke 失败（{fails}）"); return 1
    print("\n✓ 决策重放 + 本体版本化 smoke 全通过：复现·反事实·版本敏感·不可变")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
