"""HIL 待复核在 ask 回路如实 surface —— 低置信高风险动作不冒充 committed。

grass 出一地一方 的 HilPolicy：confidence < 0.75 → 待「乡土草种合规官」复核。
此前 Session 把 pending_hil 当 committed 返回（ActionResult.committed 恒 True），本组测试锁住修复：
pending_hil 是独立回复类型——数据已暂存，但副作用挂起、待复核。
"""
from clife_onto_engine.intent.compiler import CompiledIntent
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

import plugins.grass  # noqa: F401
from plugins.grass import seed_reference_data


class _FixedAction:
    """返回合规（碱茅）出一地一方，置信度由 _confidence 决定（触发/不触发 HIL）。"""
    def __init__(self, confidence):
        self._c = confidence

    def compile(self, ontology_id, utterance, *, memory_text="", actor_role=None):
        return CompiledIntent("action", action="出一地一方", confidence=self._c,
                              params={"site_id": "parcel_001", "species": ["碱茅"],
                                      "budget": 300, "_confidence": self._c})


def _seed():
    s = InMemoryStore()
    s.put_object("Site", "parcel_001", {"parcel_id": "parcel_001", "region": "巴彦淖尔", "site_type": "盐碱"})
    seed_reference_data(s)
    return s


def _session(confidence):
    return Session(ontology_id="grass", registry=spi.registry, store=_seed(),
                   compiler=_FixedAction(confidence), actor=Actor("u", "施工方"),
                   schema_version="grass@0.1.0")


def test_low_confidence_surfaces_pending_hil():
    r = _session(0.5).ask("给 parcel_001 出方案用碱茅预算300")
    assert r.kind == "pending_hil"          # 不再冒充 committed
    assert r.reviewer == "乡土草种合规官"     # 待复核角色如实带出
    assert r.written                        # 数据已暂存（写库发生）


def test_high_confidence_still_commits():
    r = _session(0.9).ask("给 parcel_001 出方案用碱茅预算300")
    assert r.kind == "committed"
    assert r.reviewer == ""


def test_pending_hil_withholds_side_effects():
    """引擎层：pending_hil 时副作用挂起（不 schedule），committed 时才派。"""
    eng = ActionEngine(spi.registry, store=_seed())
    low = eng.execute("grass", "出一地一方",
                      {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300, "_confidence": 0.5},
                      Actor("u", "施工方"), schema_version="grass@0.1.0")
    assert low.decision == "pending_hil" and low.hil_required
    assert low.effects_scheduled == ()      # 副作用挂起，待复核
    assert low.written                      # 但数据已原子落库

    high = eng.execute("grass", "出一地一方",
                       {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300, "_confidence": 0.9},
                       Actor("u", "施工方"), schema_version="grass@0.1.0")
    assert high.decision == "committed"
    assert high.effects_scheduled != ()     # 高置信直接派副作用


def test_web_serializes_pending_hil():
    from clife_onto_engine.session import Reply
    from clife_onto_engine.web import reply_to_json
    out = reply_to_json(Reply("pending_hil", 0.5, written=(("Project", "proj_x"),),
                              reviewer="乡土草种合规官"))
    assert out["kind"] == "pending_hil"
    assert out["pending_review"] is True
    assert out["reviewer"] == "乡土草种合规官"
    assert out["written"] == [["Project", "proj_x"]]
