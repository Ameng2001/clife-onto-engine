"""声明式授权策略（生产化·多租户地基）—— "谁能做什么"。

引擎在 guard 之前先过授权门：调用者角色无权执行某动作，就在**任何执行/暂存之前**
结构化拒绝并审计（decision=unauthorized）。策略**租户可配**（注入不同 AuthzPolicy 即不同授权），
与插件的业务 guard 分离——插件声明"这动作需要什么"，租户配置"谁被授权"。

默认：引擎不注入 AuthzPolicy 时授权门不启用（向后兼容）；注入后由策略裁决，可 default-deny。
与行业无关（CI 强制）：只按 (ontology, action, role) 判定，不含行业词汇。
"""
from __future__ import annotations

from pathlib import Path

import yaml


class AuthzPolicy:
    """(ontology, action) → 允许角色集合。未声明的动作按 default_allow 处理。"""

    def __init__(self, *, default_allow: bool = False) -> None:
        self._rules: dict[tuple[str, str], frozenset] = {}
        self.default_allow = default_allow

    def grant(self, ontology_id: str, action: str, *roles: str) -> "AuthzPolicy":
        key = (ontology_id, action)
        self._rules[key] = self._rules.get(key, frozenset()) | frozenset(roles)
        return self

    def allows(self, ontology_id: str, action: str, role: str) -> bool:
        key = (ontology_id, action)
        if key in self._rules:
            return role in self._rules[key]
        return self.default_allow

    def granted_roles(self, ontology_id: str, action: str) -> frozenset:
        return self._rules.get((ontology_id, action), frozenset())

    # ---- YAML 加载（租户配置：声明即 PR）----
    def load_yaml(self, ontology_id: str, path: str | Path) -> "AuthzPolicy":
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if "default_allow" in doc:
            self.default_allow = bool(doc["default_allow"])
        for raw in doc.get("grants", []):
            self.grant(ontology_id, raw["action"], *raw.get("roles", []))
        return self


class TenantAccessPolicy:
    """租户 → 可访问本体集合。服务边界据此拦跨租户/跨本体请求（入口 403，不进引擎）。

    与 Capability 内作用域互补：Capability 管"本 ontology 内只能碰已声明的对象"，
    本策略管"哪个租户能碰哪个 ontology"——边界 + 内隔离双层。默认 default_allow=False。
    """

    def __init__(self, *, default_allow: bool = False) -> None:
        self._rules: dict[str, frozenset] = {}
        self.default_allow = default_allow

    def grant(self, tenant_id: str, *ontologies: str) -> "TenantAccessPolicy":
        self._rules[tenant_id] = self._rules.get(tenant_id, frozenset()) | frozenset(ontologies)
        return self

    def allows(self, tenant_id: str, ontology_id: str) -> bool:
        if tenant_id in self._rules:
            return ontology_id in self._rules[tenant_id]
        return self.default_allow

    def allowed_ontologies(self, tenant_id: str) -> frozenset:
        return self._rules.get(tenant_id, frozenset())

    def load_yaml(self, path: str | Path) -> "TenantAccessPolicy":
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if "default_allow" in doc:
            self.default_allow = bool(doc["default_allow"])
        for raw in doc.get("tenants", []):
            self.grant(raw["tenant"], *raw.get("ontologies", []))
        return self
