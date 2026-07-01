"""启动数智本体引擎 HTTP 服务（生产化可配：租户数据接入 + 认证/租户边界/授权门）。

后端 / 本体：
  ONTO_BACKEND=memory（默认）| nebula
  ONTO_ONTOLOGIES=grass,chili（默认）
  NEBULA_HOST=127.0.0.1 NEBULA_PORT=9669（nebula 后端用）

数据来源（按本体，可选）：
  ONTO_TENANTS="grass=tenants/mengcao/tenant.yaml;chili=..."  # 声明式租户数据（按 schema 校验落库）
  未声明的本体回退到 repl 的 demo seed（向后兼容）。

访问控制（A 弧，均可选；不设即不启用，向后兼容）：
  ONTO_AUTHZ="grass=deploy/authz.grass.yaml"   # 每本体授权门（(action)->角色）
  ONTO_TENANT_POLICY=deploy/tenant_policy.yaml # 租户→可访问本体边界（跨租户 403）
  ONTO_IDENTITY=deploy/identity.yaml           # api_key→Principal（认证：无效 401，用认证身份驱动边界/授权）

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

from clife_onto_engine.authz import AuthzPolicy, TenantAccessPolicy
from clife_onto_engine.identity import StaticIdentityResolver
from clife_onto_engine.intent import IntentCompiler, OpenAICompatibleClient
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import Actor, spi
from clife_onto_engine.tenant import load_tenant
from clife_onto_engine.web import create_app

import plugins.grass  # noqa: F401  注册本体
import plugins.chili  # noqa: F401
from repl import seed  # demo 数据 seed（未声明租户数据的本体回退用）

_ACTORS = {"grass": Actor("u1", "施工方"), "chili": Actor("u1", "种植户")}


def _resolve(path: str) -> pathlib.Path:
    return pathlib.Path(path) if os.path.isabs(path) else ROOT / path


def _parse_map(env_val: str) -> dict:
    """解析 "k=v;k2=v2" → {k: v}。"""
    out: dict = {}
    for part in (env_val or "").split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _make_store(ontology: str, tenants: dict):
    backend = os.getenv("ONTO_BACKEND", "memory").lower()
    store: object
    if backend == "nebula":
        from clife_onto_engine.query.nebula_store import NebulaGraphStore
        host, port = os.getenv("NEBULA_HOST", "127.0.0.1"), int(os.getenv("NEBULA_PORT", "9669"))
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
    else:
        store = InMemoryStore()

    # 数据来源：声明了租户清单 → 按 schema 校验落库；否则回退 demo seed
    if ontology in tenants:
        report = load_tenant(_resolve(tenants[ontology]), spi.registry, store)
        print(f"[{ontology}] 租户数据接入：载入 {report.total_loaded} · 拒绝 {report.total_rejected}")
        if report.total_rejected:
            print(report.summary())
    else:
        seed(store, ontology)
        print(f"[{ontology}] demo seed（未声明租户数据）")
    return store


def _build_authz(names: list):
    cfg = _parse_map(os.getenv("ONTO_AUTHZ", ""))
    if not cfg:
        return None
    policy = AuthzPolicy(default_allow=False)
    for ont, path in cfg.items():
        policy.load_yaml(ont, _resolve(path))
        print(f"[authz] {ont} ← {path}")
    return policy


def _build_tenant_policy():
    path = os.getenv("ONTO_TENANT_POLICY", "")
    if not path:
        return None
    print(f"[tenant-policy] ← {path}")
    return TenantAccessPolicy().load_yaml(_resolve(path))


def _build_identity():
    import yaml
    path = os.getenv("ONTO_IDENTITY", "")
    if not path:
        return None
    doc = yaml.safe_load(_resolve(path).read_text(encoding="utf-8")) or {}
    resolver = StaticIdentityResolver()
    for k in doc.get("keys", []):
        resolver.add(k["api_key"], k["tenant"], k["actor_id"], k["role"])
    print(f"[identity] ← {path}（{len(doc.get('keys', []))} 凭据）")
    return resolver


def build() -> "object":
    names = [x.strip() for x in os.getenv("ONTO_ONTOLOGIES", "grass,chili").split(",") if x.strip()]
    tenants = _parse_map(os.getenv("ONTO_TENANTS", ""))
    ontologies = {n: {"store": _make_store(n, tenants), "actor": _ACTORS.get(n, Actor("u1", "用户"))}
                  for n in names}

    def make_compiler():
        client = OpenAICompatibleClient(config_path=str(ROOT / "llm.local.json"))
        return IntentCompiler(client, spi.registry)

    cyto = ROOT / "third-party" / "okf-visualizer" / "reference_agent" / "viewer" / "static" / "vendor" / "cytoscape.min.js"
    explorer_js = cyto.read_text(encoding="utf-8") if cyto.exists() else ""
    # OKF 知识图谱 viz（build/okf/<ont>/viz.html，自包含）：存在即上架 /viz/<ont>
    viz_html: dict = {}
    for n in names:
        vp = ROOT / "build" / "okf" / n / "viz.html"
        if vp.exists():
            viz_html[n] = vp.read_text(encoding="utf-8")
            print(f"[{n}] OKF viz 上架 /viz/{n}")
        else:
            print(f"[{n}] 无 OKF viz（跑 python scripts/export_okf.py 生成 build/okf/{n}/viz.html）")
    return create_app(ontologies=ontologies, make_compiler=make_compiler, explorer_js=explorer_js,
                      authz=_build_authz(names), tenant_policy=_build_tenant_policy(),
                      identity_resolver=_build_identity(), viz_html=viz_html)


app = build()


def main() -> None:
    import uvicorn
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    print(f"== 数智本体引擎 HTTP 服务 · http://{host}:{port}  （/docs 看接口）==")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
