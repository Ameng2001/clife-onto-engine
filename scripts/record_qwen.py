"""录制真 Qwen 对语料每句口语的**原始 JSON 输出** → fixture（record-replay 的录制端）。

跑一次（需 llm.local.json / DASHSCOPE_API_KEY + 网络），把真 Qwen 编译行为固化到
tests/fixtures/qwen_replay.json；CI 用 ReplayLLMClient 重放，无需 key/网络。

运行：python scripts/record_qwen.py   # 真 Qwen 录制，覆盖 fixture
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.intent.llm import ReplayLLMClient
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401
from e2e_corpus import SCENARIOS, _seed

FIXTURE = ROOT / "tests" / "fixtures" / "qwen_replay.json"


class _Recorder:
    """包住真客户端，按口语键录下每次 complete_json 的原始 JSON。"""
    def __init__(self, inner):
        self.inner = inner
        self.rec: dict = {}

    def complete_json(self, system: str, user: str) -> dict:
        out = self.inner.complete_json(system, user)
        self.rec[ReplayLLMClient.utterance_of(user)] = out
        return out


def main() -> int:
    client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
    print(f"== 录制真 Qwen · model={client.model} ==")
    rec = _Recorder(client)
    compiler = IntentCompiler(rec, spi.registry)

    sessions: dict = {}
    for sc in SCENARIOS:
        key = (sc.ontology, sc.actor_role)
        if key not in sessions:
            sessions[key] = Session(ontology_id=sc.ontology, registry=spi.registry,
                                    store=_seed(sc.ontology), compiler=compiler,
                                    actor=Actor("u", sc.actor_role), session_id=f"{key}",
                                    schema_version=f"{sc.ontology}@0.1.0", load_knowledge=True)
        sessions[key].ask(sc.utterance)
        print(f"  ✓ 录制「{sc.utterance}」")

    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(rec.rec, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\n== 已写 {len(rec.rec)} 条录制 → {FIXTURE.relative_to(ROOT)} ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
