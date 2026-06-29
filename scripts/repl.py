"""统一应用门面的 CLI —— 一句口语进，做/查/澄清出。

跑完整回路：意图编译路由 →（查：OQL ／ 做：Action 引擎 guard/写后规则/回滚/审计）→ 结构化结果。

交互：  python scripts/repl.py [grass|chili]      # 敲中文，回车
管道：  echo "巴彦淖尔有哪些地块？" | python scripts/repl.py grass
命令：  /help /audit /mem /quit
前置：  llm.local.json + pip install openai
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine import Session
from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.query import InMemoryStore, StagedLink
from clife_onto_engine.sdk import Actor, spi

_ACTORS = {"grass": ("u1", "施工方"), "chili": ("u1", "种植户")}


def seed(store: InMemoryStore, ontology: str) -> None:
    if ontology == "grass":
        import plugins.grass as g
        g.seed_reference_data(store)  # Site parcel_001 + 乡土名录
        store.put_object("Site", "parcel_002", {"parcel_id": "parcel_002", "region": "锡林郭勒", "site_type": "草原"})
        store.put_object("Degradation", "deg1", {"deg_id": "deg1", "level": "重度", "type": "盐渍化"})
        store.put_object("RestorationMethod", "m_喷播", {"method_id": "m_喷播", "name": "喷播"})
        store.put_object("RestorationMethod", "m_补播", {"method_id": "m_补播", "name": "补播"})
        store.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg1"))
        store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_喷播"))
        store.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m_补播"))
    elif ontology == "chili":
        import plugins.chili as c
        c.seed_reference_data(store)
    else:
        raise SystemExit(f"未知本体: {ontology}（可选 grass / chili）")


def build_session(ontology: str) -> Session:
    seed_store = InMemoryStore()
    seed(seed_store, ontology)
    client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
    actor = Actor(*_ACTORS.get(ontology, ("u1", "用户")))
    return Session(ontology_id=ontology, registry=spi.registry, store=seed_store,
                   compiler=IntentCompiler(client, spi.registry), actor=actor,
                   schema_version=f"{ontology}@0.1.0")


def main() -> None:
    ontology = sys.argv[1] if len(sys.argv) > 1 else "grass"
    session = build_session(ontology)
    print(f"== 数智本体会话 · 本体={ontology} · 角色={session.actor.role} · 模型={session.compiler.client.model} ==")
    print("   敲中文问/做事；/help 帮助，/quit 退出\n")
    for line in sys.stdin:
        utt = line.strip()
        if not utt:
            continue
        if utt in ("/quit", "/exit", "quit", "exit"):
            break
        if utt == "/help":
            print("  问数据：『巴彦淖尔有哪些地块？』『parcel_001 能用哪些修复方法？』")
            print("  做动作：『给 parcel_001 出一地一方，用碱茅披碱草，预算300』")
            print("  /audit 看最近审计  /mem 看记忆  /quit 退出"); continue
        if utt == "/audit":
            for s in session.engine.audit.query(ontology)[-3:]:
                print(f"  audit: {s.action} decision={s.decision} conf={s.confidence} evidence={len(s.evidence)}")
            continue
        if utt == "/mem":
            from clife_onto_engine.memory import Layer
            print(f"  CONTEXT 记忆 {len(session.memory.by_layer(Layer.CONTEXT, ontology, session.session_id))} 条")
            continue
        try:
            reply = session.ask(utt)
            print(f"  {reply.summary()}\n")
        except Exception as e:  # noqa: BLE001 — REPL 兜底，单句失败不退出
            print(f"  [异常] {e}\n")


if __name__ == "__main__":
    main()
