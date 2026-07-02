"""real-Qwen 回归（record-replay）：回放录制的真 Qwen 原始输出，编译器逐字跑真实解析/校验。

把 #27–#35 的"真 Qwen 手工抽检"固化为 CI 门控回归——确定性、无 key/网络。
录制端：scripts/record_qwen.py（真 Qwen，改本体/语料后需重录）。
"""
from __future__ import annotations

import json
import pathlib

from clife_onto_engine.intent.compiler import IntentCompiler
from clife_onto_engine.intent.llm import ReplayLLMClient
from clife_onto_engine.sdk import spi

from scripts.e2e_corpus import SCENARIOS, run

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "qwen_replay.json"


def _recordings():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_covers_every_utterance():
    rec = _recordings()
    missing = {s.utterance for s in SCENARIOS} - set(rec)
    assert not missing, f"fixture 缺录制（重跑 record_qwen.py）：{missing}"


def test_qwen_replay_corpus_all_pass():
    """真 Qwen 原始输出经编译器 → Session，逐条 kind + 结果断言全过（含拒绝=0 不安全落库）。"""
    compiler = IntentCompiler(ReplayLLMClient(_recordings()), spi.registry)
    passed, failed = run(SCENARIOS, compiler=compiler)
    assert failed == 0 and passed == len(SCENARIOS)
