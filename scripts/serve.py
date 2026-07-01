"""启动数智本体引擎 HTTP 服务。

后端由环境变量选择：
  ONTO_BACKEND=memory（默认）| nebula
  ONTO_ONTOLOGIES=grass,chili（默认）
  NEBULA_HOST=127.0.0.1 NEBULA_PORT=9669（nebula 后端用）
LLM 凭据从 env（DASHSCOPE_*/OPENAI_*）或 llm.local.json 读取。

运行：python scripts/serve.py [host] [port]   # 默认 127.0.0.1:8000；/docs 看接口
"""
from __future__ import annotations

import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi
from clife_onto_engine.web import create_app

from repl import seed  # 复用 REPL 的 demo 数据 seed

_ACTORS = {"grass": Actor("u1", "施工方"), "chili": Actor("u1", "种植户")}


def _make_store(ontology: str):
    backend = os.getenv("ONTO_BACKEND", "memory").lower()
    if backend == "nebula":
        from clife_onto_engine.query.nebula_store import NebulaGraphStore
        host = os.getenv("NEBULA_HOST", "127.0.0.1")
        port = int(os.getenv("NEBULA_PORT", "9669"))
        last = None
        for _ in range(40):  # 等 graphd 起来
            try:
                store = NebulaGraphStore(ontology_id=ontology, registry=spi.registry,
                                         hosts=[(host, port)]).connect()
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2)
        else:
            raise RuntimeError(f"连不上 NebulaGraph {host}:{port}: {last}")
        print(f"[{ontology}] bootstrap NebulaGraph（建库建模，DDL 等待中…）")
        store.bootstrap(drop=True)
        seed(store, ontology)        # 参考数据写入 Nebula
        return store
    s = InMemoryStore()
    seed(s, ontology)
    return s


def build() -> "object":
    names = [x.strip() for x in os.getenv("ONTO_ONTOLOGIES", "grass,chili").split(",") if x.strip()]
    ontologies = {n: {"store": _make_store(n), "actor": _ACTORS.get(n, Actor("u1", "用户"))}
                  for n in names}
    def make_compiler():
        client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
        return IntentCompiler(client, spi.registry)
    # vendored cytoscape 注入 → /explorer 离线自包含（自有对象图浏览）
    cyto = ROOT / "third-party" / "okf-visualizer" / "reference_agent" / "viewer" / "static" / "vendor" / "cytoscape.min.js"
    explorer_js = cyto.read_text(encoding="utf-8") if cyto.exists() else ""
    return create_app(ontologies=ontologies, make_compiler=make_compiler, explorer_js=explorer_js)


app = build()


def main() -> None:
    import uvicorn
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    print(f"== 数智本体引擎 HTTP 服务 · http://{host}:{port}  （/docs 看接口）==")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
