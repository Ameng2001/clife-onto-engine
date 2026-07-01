"""端到端场景语料（桩模式）：读/写全面覆盖锁 CI —— 两插件 4 动作各提交+拒绝、多种读、advise、clarify。"""
from __future__ import annotations

from scripts.e2e_corpus import SCENARIOS, run

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401


def test_corpus_all_pass_stub():
    passed, failed = run(SCENARIOS, force_stub=True)
    assert failed == 0 and passed == len(SCENARIOS)


def test_covers_all_four_actions():
    # 写面覆盖两插件全部 4 个动作，且各有提交与拒绝
    acts = {}
    for s in SCENARIOS:
        if s.face == "写":
            acts.setdefault(s.stub_intent.action, set()).add(s.expect_kind)
    assert set(acts) == {"出一地一方", "快检评级", "制定种植方案", "辣椒分级"}
    assert all({"committed", "rejected"} <= v for v in acts.values())


def test_covers_read_faces():
    reads = [s for s in SCENARIOS if s.face == "读"]
    # 简单/多跳/聚合 + chili 各类读
    assert any(s.stub_intent.oql.steps for s in reads)          # 多跳
    assert any(s.stub_intent.oql.aggregate for s in reads)      # 聚合
    assert {s.ontology for s in reads} == {"grass", "chili"}    # 两插件


def test_covers_advise_and_clarify():
    kinds = {s.expect_kind for s in SCENARIOS}
    assert {"advise", "clarify", "query", "committed", "rejected"} <= kinds
