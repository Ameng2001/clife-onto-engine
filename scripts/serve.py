"""启动数智本体引擎 HTTP 服务（grass + chili 双本体）。

前置：pip install -r requirements-server.txt  且  llm.local.json 配好
运行：python scripts/serve.py            # 默认 127.0.0.1:8000
文档：浏览器开 http://127.0.0.1:8000/docs （FastAPI 自动 OpenAPI）

示例：
  curl -s localhost:8000/ontologies
  curl -s localhost:8000/manifest/grass
  curl -s -XPOST localhost:8000/ask -H 'content-type: application/json' \
       -d '{"ontology":"grass","utterance":"巴彦淖尔有哪些地块？"}'
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.sdk import Actor, spi
from clife_onto_engine.web import create_app

from repl import seed  # 复用 REPL 的 demo 数据 seed


def build() -> "object":
    ontologies = {
        "grass": {"seed": lambda s: seed(s, "grass"), "actor": Actor("u1", "施工方")},
        "chili": {"seed": lambda s: seed(s, "chili"), "actor": Actor("u1", "种植户")},
    }
    def make_compiler():
        client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
        return IntentCompiler(client, spi.registry)
    return create_app(ontologies=ontologies, make_compiler=make_compiler)


app = build()


def main() -> None:
    import uvicorn
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    print(f"== 数智本体引擎 HTTP 服务 · http://{host}:{port}  （/docs 看接口）==")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
