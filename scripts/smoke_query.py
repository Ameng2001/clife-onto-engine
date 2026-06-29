"""冒烟：意图编译器的 OQL 查路径（真 Qwen）—— NL → 结构化 OQL → schema 校验 → 执行。

补全"会查"那一半：编译器从"只会做(action)"扩成"会做、会查(query)、要澄清"。
查路径不是 RAG：把口语翻成**受 schema 约束、防注入的结构化 OQL**，在治理图谱上查。

前置：llm.local.json + pip install openai
运行：python scripts/smoke_query.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.query import InMemoryStore, QueryView, StagedLink
from clife_onto_engine.query.oql import execute
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401

NS = "grass"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def seed(store: InMemoryStore) -> None:
    store.put_object("Site", "parcel_001", {"parcel_id": "parcel_001", "region": "巴彦淖尔", "site_type": "盐碱"})
    store.put_object("Site", "parcel_002", {"parcel_id": "parcel_002", "region": "锡林郭勒", "site_type": "草原"})
    store.put_object("Degradation", "deg1", {"deg_id": "deg1", "level": "重度", "type": "盐渍化"})
    store.put_object("RestorationMethod", "m_喷播", {"method_id": "m_喷播", "name": "喷播"})
    store.put_object("RestorationMethod", "m_补播", {"method_id": "m_补播", "name": "补播"})
    store.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg1"))
    store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_喷播"))
    store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_补播"))


def main() -> None:
    compiler = IntentCompiler(OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json")),
                              spi.registry)
    store = InMemoryStore(); seed(store)
    print(f"模型: {compiler.client.model}\n")

    utterances = [
        "巴彦淖尔有哪些地块？",
        "parcel_001 这块地能用哪些修复方法？",
        "锡林郭勒有几个地块？",
        "给 parcel_001 出个一地一方方案，用碱茅，预算300",   # 路由测试 → action
    ]
    for utt in utterances:
        ci = compiler.compile(NS, utt, actor_role="施工方")
        print(f"「{utt}」→ [{ci.kind}] conf={ci.confidence:.2f}")
        if ci.is_query:
            r = execute(ci.oql, QueryView(store, []), spi.registry)
            print(f"    OQL: start={ci.oql.start} where={[(c.field,c.op,c.value) for c in ci.oql.where]} "
                  f"steps={[s.link_type for s in ci.oql.steps]}")
            print(f"    结果: {r.rows}  成本={r.cost}")
        elif ci.executable:
            print(f"    → action {ci.action} {ci.params}")
        else:
            print(f"    → {ci.question or ci.error}")
        print()


if __name__ == "__main__":
    main()
