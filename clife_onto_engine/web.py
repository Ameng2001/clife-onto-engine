"""HTTP API —— 把 Session 门面包成服务（FastAPI 薄适配）。

一个端点 `POST /ask` 收口完整回路：一句口语 →（做/查/澄清）→ 结构化 JSON。
compiler 用工厂注入（make_compiler），故 web 层不绑死真 LLM —— 可注入 stub 离线测试。
与行业无关（CI 强制）。fastapi/uvicorn 为可选依赖（见 requirements-server.txt）。

    from clife_onto_engine.web import create_app
    app = create_app(ontologies={...}, make_compiler=lambda: IntentCompiler(...))
"""
# 注意：本模块不要用 `from __future__ import annotations` —— 那会把 FastAPI 端点里
# 局部 Pydantic 模型的注解变成字符串，FastAPI 无法从模块全局解析局部类，导致 body 被
# 误判为 query 参数（422）。

from typing import Callable

from .intent import build_manifest
from .kernel import ActionEngine
from .query import InMemoryStore
from .session import Reply, Session
from .sdk import spi


def reply_to_json(r: Reply) -> dict:
    out: dict = {"kind": r.kind, "confidence": r.confidence}
    if r.kind == "query":
        out["rows"] = r.rows
        out["cost"] = r.cost
        if r.oql is not None:
            out["query"] = {
                "start": r.oql.start,
                "where": [[c.field, c.op, c.value] for c in r.oql.where],
                "steps": [s.link_type for s in r.oql.steps],
            }
    elif r.kind == "committed":
        out["written"] = [list(w) for w in r.written]
    elif r.kind == "rejected":
        out["violations"] = [
            {"rule": v.rule, "message": v.message, "suggestion": v.suggestion} for v in r.violations
        ]
    elif r.kind == "clarify":
        out["question"] = r.question
    else:
        out["error"] = r.error
    return out


def create_app(*, ontologies: dict, make_compiler: Callable, explorer_js: str = "",
               tenant_policy=None, identity_resolver=None):
    """ontologies: {name: {"store": GraphStore, "actor": Actor}}；make_compiler: () -> IntentCompiler。

    store 由调用方建好（InMemory 或 NebulaGraph，已 seed/bootstrap）—— web 层与后端解耦。
    explorer_js: vendored cytoscape JS（调用方注入）→ /explorer 内联即离线；空则 Explorer 走 CDN。
    tenant_policy: TenantAccessPolicy（可选）—— 设了则各本体端点强制"租户→本体"边界（跨租户 403）；
                   None 时不启用（向后兼容）。
    """
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel

    app = FastAPI(title="clife-onto-engine",
                  description="数智本体引擎 HTTP API —— 一句口语：做/查/澄清，本体兜底。")

    # 每本体一份 store + engine（共享审计/journal）；compiler 惰性、跨会话共享。
    backends: dict = {}
    for name, cfg in ontologies.items():
        store = cfg["store"]
        backends[name] = {"store": store, "engine": ActionEngine(spi.registry, store=store),
                          "actor": cfg["actor"]}
    _state: dict = {"compiler": None}
    sessions: dict = {}

    def _compiler():
        if _state["compiler"] is None:
            _state["compiler"] = make_compiler()
        return _state["compiler"]

    def _check_tenant(ont: str, tenant: str = "") -> None:
        # 服务边界：设了 tenant_policy 就强制"租户→本体"访问（跨租户/跨本体 403，不进引擎）。
        if tenant_policy is not None and not tenant_policy.allows(tenant, ont):
            raise HTTPException(status_code=403,
                                detail=f"租户 '{tenant}' 无权访问本体 '{ont}'")

    def _resolve(x_api_key: str, claimed_tenant: str):
        """认证优先：设了 identity_resolver 则凭据必须解析出 Principal（否则 401），
        用 Principal.tenant/actor；未设则用声明 tenant + 后端默认 actor（向后兼容）。"""
        if identity_resolver is not None:
            p = identity_resolver.resolve(x_api_key or "")
            if p is None:
                raise HTTPException(status_code=401, detail="凭据无效或缺失")
            return p.tenant, p.actor
        return claimed_tenant, None

    def _session(ont: str, sid: str, actor=None) -> Session:
        if ont not in backends:
            raise HTTPException(status_code=404, detail=f"未知本体: {ont}")
        b = backends[ont]
        act = actor if actor is not None else b["actor"]
        key = (ont, sid, act.id)              # 认证身份不同 → 独立会话记忆
        if key not in sessions:  # 每 (本体,会话,身份) 独立记忆，共享本体 store/engine
            sessions[key] = Session(ontology_id=ont, registry=spi.registry, store=b["store"],
                                    compiler=_compiler(), actor=act, session_id=sid,
                                    engine=b["engine"], schema_version=f"{ont}@0.1.0")
        return sessions[key]

    class AskBody(BaseModel):
        ontology: str
        utterance: str
        session_id: str = "default"
        tenant: str = ""              # 多租户边界（设了 tenant_policy 时校验）

    class PlanBody(BaseModel):
        ontology: str
        object_type: str
        key: str
        series: str
        params: dict = {}
        tenant: str = ""

    @app.get("/health")
    def health():
        return {"status": "ok", "ontologies": list(backends)}

    @app.get("/ontologies")
    def list_ontologies():
        return {"ontologies": list(backends)}

    @app.get("/manifest/{ontology}")
    def manifest(ontology: str, tenant: str = "", x_api_key: str = Header(default="")):
        eff_tenant, _ = _resolve(x_api_key, tenant)
        _check_tenant(ontology, eff_tenant)
        if ontology not in backends:
            raise HTTPException(status_code=404, detail=f"未知本体: {ontology}")
        return build_manifest(spi.registry, ontology)

    @app.get("/audit/{ontology}")
    def audit(ontology: str, limit: int = 10, tenant: str = "", x_api_key: str = Header(default="")):
        eff_tenant, _ = _resolve(x_api_key, tenant)
        _check_tenant(ontology, eff_tenant)
        if ontology not in backends:
            raise HTTPException(status_code=404, detail=f"未知本体: {ontology}")
        snaps = backends[ontology]["engine"].audit.query(ontology)[-limit:]
        return {"audit": [{"action": s.action, "decision": s.decision,
                           "confidence": s.confidence, "evidence": list(s.evidence)} for s in snaps]}

    @app.post("/ask")
    def ask(body: AskBody, x_api_key: str = Header(default="")):
        eff_tenant, actor = _resolve(x_api_key, body.tenant)
        _check_tenant(body.ontology, eff_tenant)
        return reply_to_json(_session(body.ontology, body.session_id, actor).ask(body.utterance))

    @app.get("/explorer/{ontology}", response_class=HTMLResponse)
    def explorer(ontology: str, tenant: str = "", x_api_key: str = Header(default="")):
        # 自有对象图 Explorer：从活 store 现场渲染，浏览实时治理状态（不需 UModel）。
        from .explorer import render
        eff_tenant, _ = _resolve(x_api_key, tenant)
        _check_tenant(ontology, eff_tenant)
        if ontology not in backends:
            raise HTTPException(status_code=404, detail=f"未知本体: {ontology}")
        return render(spi.registry, backends[ontology]["store"], ontology,
                     cytoscape_js=explorer_js)

    @app.post("/plan")
    def plan(body: PlanBody, x_api_key: str = Header(default="")):
        # 遥测查询计划：引擎据对象绑定产计划（PromQL/ES/SQL，id 已代入），不执行。
        from .query.telemetry import build_plan
        eff_tenant, _ = _resolve(x_api_key, body.tenant)
        _check_tenant(body.ontology, eff_tenant)
        if body.ontology not in backends:
            raise HTTPException(status_code=404, detail=f"未知本体: {body.ontology}")
        return build_plan(spi.registry, backends[body.ontology]["store"],
                          body.object_type, body.key, body.series,
                          namespace=body.ontology, params=body.params)

    return app
