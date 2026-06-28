"""冒烟：意图编译器（真 LLM·Qwen）—— NL → 校验后的结构化意图 → 真 Action 引擎。

前置：llm.local.json 配好（base_url/model/api_key），pip install openai
运行：python scripts/smoke_intent.py

证明：自然语言经能力清单约束 + 内核确定性校验，落到已建的 Action 流水线真 commit；
越界/缺参/超范围分别走 拒绝/澄清。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine import ActionEngine
from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi

from plugins.grass import seed_reference_data

NS = "grass"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> None:
    client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
    compiler = IntentCompiler(client, spi.registry)
    print(f"== 模型: {client.model} ==\n")

    utterances = [
        ("我家盐碱地 parcel_001 想低成本修复，用碱茅和披碱草，预算每亩300", "施工方"),
        ("帮我看下这批草 batch=B202606，CP20 NDF38 ADF30 RFV160，没霉变", "养殖户"),
        ("给我修复一下草场吧", "牧民"),                 # 缺必填 → 澄清
        ("今天呼和浩特天气怎么样", "牧民"),              # 超范围 → 澄清
    ]
    compiled = []
    for utt, role in utterances:
        ci = compiler.compile(NS, utt, actor_role=role)
        compiled.append(ci)
        line = f"[{ci.kind}] conf={ci.confidence:.2f}"
        if ci.kind == "action":
            line += f" → {ci.action} {ci.params}"
        elif ci.kind == "clarify":
            line += f" → 追问: {ci.question}"
        else:
            line += f" → {ci.error}"
        print(f"  「{utt}」\n    {line}\n")

    print("== 端到端：把第一条编译出的 Action 意图交给真引擎执行 ==")
    store = InMemoryStore()
    seed_reference_data(store)
    engine = ActionEngine(spi.registry, store=store)
    ci = compiled[0]
    if ci.executable:
        res = engine.execute(NS, ci.action, ci.params, Actor("u1", "施工方"),
                             schema_version="grass@0.1.0", ts="2026-06-28T16:00:00")
        print(f"  NL→Action 执行: committed={res.committed} "
              f"written={getattr(res, 'written', None) or [v.rule for v in getattr(res,'violations',())]}")
        sp_key = "sp_" + str(ci.params["site_id"])
        print(f"  读回: {store.get_object('SeedPack', sp_key)}")
    else:
        print(f"  第一条不可执行（{ci.kind}），跳过")


if __name__ == "__main__":
    main()
