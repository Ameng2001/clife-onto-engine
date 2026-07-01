"""服务边界身份解析（生产化·多租户）—— 把凭据认证成 Principal(tenant/actor/role)。

授权门（谁能做）与租户边界（哪租户碰哪本体）此前用的是**客户端声明**的 tenant/actor；
本模块把身份从"声明"换成"认证"：请求出示凭据 → resolver 解析成 Principal → 用**认证身份**判定。
resolver 可插拔：`StaticIdentityResolver`（api_key→Principal，简单部署/测试）；真部署注入 JWT/OIDC。

与行业无关（CI 强制）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from .sdk.context import Actor


@dataclass(frozen=True)
class Principal:
    tenant: str
    actor_id: str
    role: str

    @property
    def actor(self) -> Actor:
        return Actor(self.actor_id, self.role)


class IdentityResolver(Protocol):
    def resolve(self, credential: str) -> Optional[Principal]:
        ...


class StaticIdentityResolver:
    """静态凭据表：api_key → Principal。简单部署/测试用；真部署换 JWT/OIDC 实现同协议。"""

    def __init__(self, keys: Optional[dict] = None) -> None:
        self._keys: dict[str, Principal] = dict(keys or {})

    def add(self, api_key: str, tenant: str, actor_id: str, role: str) -> "StaticIdentityResolver":
        self._keys[api_key] = Principal(tenant, actor_id, role)
        return self

    def resolve(self, credential: str) -> Optional[Principal]:
        return self._keys.get(credential)
