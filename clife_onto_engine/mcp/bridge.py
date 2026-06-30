"""治理写桥（传输无关核心）—— 让 MCP agent 既受治理地查、又受治理地做。

红线（与 docs/04 一致）：
  · 受治理写的**唯一入口**是 `act` → `ActionEngine`（guard→写后规则→提交/确定性回滚→审计）。
  · UModel 永远只读：只把**已彻底提交**（decision == "committed"）的状态反映进读层；
    `pending_hil`（待人工复核）与 `rejected` **不反映**。
  · 引擎不依赖读层：反映失败只记录，绝不回滚已提交的治理写。

本模块与传输解耦（JSON-RPC 在 server.py）；`Reflector` 的 HTTP poster 可注入 → 离线可测。
与行业无关（CI 强制）。
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from ..kernel import ActionEngine
from ..kernel.rejection import ActionResult
from ..query import StagedWrite  # noqa: F401  (类型参考)
from ..sdk.context import Actor
from ..session import Reply, Session
from ..web import reply_to_json
from .. import umodel as _um


def _http_post(url: str, payload: dict) -> dict:
    """默认 poster：stdlib urllib，无重依赖。"""
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (受信本地 sidecar)
        return json.loads(resp.read().decode("utf-8") or "{}")


class Reflector:
    """把**已提交**对象反映进 UModel 读层（REST entities:write）。post 可注入 → 离线可测。"""

    def __init__(self, base_url: str, ontology: str, *,
                 post: Optional[Callable[[str, dict], dict]] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.ontology = ontology
        self._post = post or _http_post

    def reflect(self, store, written: tuple) -> dict:
        """written: ((object_type, key), ...) —— 从引擎 store 读真值，成形复用导出器。"""
        entities = []
        for object_type, key in written:
            row = store.get_object(object_type, key) or {}
            rec = {
                "__domain__": self.ontology,
                "__entity_type__": _um._qualified(self.ontology, object_type),
                "__entity_id__": _um._eid(self.ontology, object_type, key),
                "__category__": "entity", "__method__": "Update",
                "__first_observed_time__": _um._OBSERVED_FROM,
                "__last_observed_time__": _um._OBSERVED_TO,
            }
            rec.update(row)
            entities.append(rec)
        if not entities:
            return {"reflected": 0}
        url = f"{self.base_url}/api/v1/entitystore/{self.ontology}/entities:write"
        resp = self._post(url, {"entities": entities})
        return {"reflected": len(entities), "response": resp}

    def reflect_relations(self, links: tuple) -> dict:
        """links: ((link_type, from_type, from_key, to_type, to_key), ...) —— 两端 id 与对象反映同公式。"""
        relations = []
        for link_type, from_type, from_key, to_type, to_key in links:
            relations.append({
                "__src_domain__": self.ontology,
                "__src_entity_type__": _um._qualified(self.ontology, from_type),
                "__src_entity_id__": _um._eid(self.ontology, from_type, from_key),
                "__dest_domain__": self.ontology,
                "__dest_entity_type__": _um._qualified(self.ontology, to_type),
                "__dest_entity_id__": _um._eid(self.ontology, to_type, to_key),
                "__relation_type__": link_type, "__category__": "entity_link", "__method__": "Update",
                "__first_observed_time__": _um._OBSERVED_FROM,
                "__last_observed_time__": _um._OBSERVED_TO,
            })
        if not relations:
            return {"relations_reflected": 0}
        url = f"{self.base_url}/api/v1/entitystore/{self.ontology}/relations:write"
        resp = self._post(url, {"relations": relations})
        return {"relations_reflected": len(relations), "relations_response": resp}


class GovernedBridge:
    """受治理工具门面：`query`（读，默认开）+ opt-in `act`（写，经引擎）。"""

    def __init__(self, *, ontology_id: str, registry, store, compiler, actor: Actor,
                 engine: Optional[ActionEngine] = None, reflector: Optional[Reflector] = None,
                 enable_act: bool = False, schema_version: str = "") -> None:
        self.ontology_id = ontology_id
        self.registry = registry
        self.store = store
        self.actor = actor
        self.engine = engine if engine is not None else ActionEngine(registry, store=store)
        self.reflector = reflector
        self.enable_act = enable_act
        self.schema_version = schema_version or f"{ontology_id}@0.1.0"
        self.session = Session(ontology_id=ontology_id, registry=registry, store=store,
                               compiler=compiler, actor=actor, engine=self.engine,
                               schema_version=self.schema_version)

    # ---- 工具清单（读默认开；写需 opt-in）----
    def tools(self) -> list[str]:
        return ["query", "plan"] + (["act"] if self.enable_act else [])

    # ---- 读：受治理（经引擎 OQL，非 UModel SPL 旁路）----
    def query(self, utterance: str) -> dict:
        return reply_to_json(self.session.ask(utterance))

    # ---- 读：遥测查询计划（引擎产计划、不执行）----
    def plan(self, object_type: str, key: str, series: str,
             params: Optional[dict] = None) -> dict:
        from ..query.telemetry import build_plan
        return build_plan(self.registry, self.store, object_type, key, series,
                          namespace=self.ontology_id, params=params)

    # ---- 写：经 Action 引擎，本体兜底；仅 committed 反映 ----
    def act(self, action: str, params: dict, *, actor_role: Optional[str] = None) -> dict:
        if not self.enable_act:
            return {"kind": "error", "error": "写工具未启用（opt-in）"}
        actor = self.actor if actor_role is None else Actor(self.actor.id, actor_role)
        try:
            res = self.engine.execute(self.ontology_id, action, params, actor,
                                      schema_version=self.schema_version)
        except Exception as e:  # 未声明动作等 → 结构化错误（与 /ask 同兜底）
            return {"kind": "error", "error": f"{type(e).__name__}: {e}"}

        # 拒绝（StructuredRejection）：结构化 violations，不反映
        if not res.committed:
            return {"kind": "rejected", "phase": getattr(res, "phase", ""),
                    "violations": [{"rule": v.rule, "message": v.message,
                                    "suggestion": v.suggestion} for v in res.violations]}

        # ActionResult：committed 或 pending_hil
        written = [list(w) for w in res.written]
        if isinstance(res, ActionResult) and res.decision == "pending_hil":
            # 待人工复核：引擎已落库，但读层等 HIL 清算 → 不反映
            return {"kind": "pending_hil", "written": written,
                    "confidence": res.confidence, "reflected": 0}

        out = {"kind": "committed", "written": written,
               "links_written": [list(l) for l in getattr(res, "links_written", ())],
               "confidence": getattr(res, "confidence", 0.0), "reflected": 0}
        # 提交后反映（失败不回滚引擎提交）：先对象、后关系（关系端点须先存在）
        if self.reflector is not None:
            try:
                out.update(self.reflector.reflect(self.store, res.written))
                if getattr(res, "links_written", ()):
                    out.update(self.reflector.reflect_relations(res.links_written))
            except Exception as e:  # 读层不可用 → 记录，不影响已提交的治理写
                out["reflect_error"] = f"{type(e).__name__}: {e}"
        return out
