"""Plugin SPI 注册中心。

内核提供注册点；插件用装饰器声明 Function / Rule / Action handler 与元数据。
内核运行时按 (ontology_id, kind, name) 解析。插件不改内核源码即可接入。

七个槽位（见 docs §4）中，本模块覆盖 1(schema 元数据)/3(function·rule)/4(action)；
映射(2)、记忆词典(5)、agent(6)、CQ(7) 由各自子系统加载，复用同一 Registry。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..metamodel import (
    ActionDef,
    Backing,
    Evaluation,
    FunctionDef,
    HilPolicy,
    ObjectType,
    LinkType,
    RuleDef,
    Severity,
)
from .errors import RegistrationError, ResolutionError
from .mapping import MappingRegistry


@dataclass
class Registry:
    objects: dict[tuple[str, str], ObjectType] = field(default_factory=dict)
    links: dict[tuple[str, str], LinkType] = field(default_factory=dict)
    functions: dict[tuple[str, str], FunctionDef] = field(default_factory=dict)
    rules: dict[tuple[str, str], RuleDef] = field(default_factory=dict)
    actions: dict[tuple[str, str], ActionDef] = field(default_factory=dict)
    mappings: MappingRegistry = field(default_factory=MappingRegistry)  # 槽位 2

    # ---- 声明式注册（schema 元数据，槽位 1）----
    def add_object(self, obj: ObjectType) -> None:
        self._guard_dup(self.objects, (obj.namespace, obj.name), "object")
        self.objects[(obj.namespace, obj.name)] = obj

    def add_link(self, link: LinkType) -> None:
        self._guard_dup(self.links, (link.namespace, link.name), "link")
        self.links[(link.namespace, link.name)] = link

    # ---- 解析 ----
    def get_action(self, ontology_id: str, name: str) -> ActionDef:
        try:
            return self.actions[(ontology_id, name)]
        except KeyError:
            raise ResolutionError(f"未注册的 Action: {ontology_id}.{name}")

    def get_rule(self, ontology_id: str, name: str) -> RuleDef:
        try:
            return self.rules[(ontology_id, name)]
        except KeyError:
            raise ResolutionError(f"未注册的 Rule: {ontology_id}.{name}")

    def get_function(self, ontology_id: str, name: str) -> FunctionDef:
        try:
            return self.functions[(ontology_id, name)]
        except KeyError:
            raise ResolutionError(f"未注册的 Function: {ontology_id}.{name}")

    @staticmethod
    def _guard_dup(table: dict, key, kind: str) -> None:
        if key in table:
            raise RegistrationError(f"重复注册 {kind}: {key[0]}.{key[1]}")


class SPI:
    """插件面向的注册门面。一个进程一份默认 Registry；测试可注入独立实例。"""

    def __init__(self, registry: Optional[Registry] = None) -> None:
        self.registry = registry or Registry()

    @property
    def mappings(self):
        return self.registry.mappings

    def load_mappings(self, ontology_id: str, yaml_path) -> None:
        """槽位 2：从 YAML 加载对象/关系的物理映射。"""
        self.registry.mappings.load_yaml(ontology_id, yaml_path)

    # 槽位 3：只读派生量
    def function(self, ontology_id: str, name: str, *, reads: tuple[str, ...] = ()):
        def deco(fn: Callable):
            self.registry._guard_dup(self.registry.functions, (ontology_id, name), "function")
            self.registry.functions[(ontology_id, name)] = FunctionDef(
                name=name, namespace=ontology_id, reads=reads, impl=fn
            )
            return fn
        return deco

    # 槽位 3：全局不变式 / guard
    def rule(
        self,
        ontology_id: str,
        name: str,
        *,
        backing: Backing = Backing.DECLARATIVE,
        severity: Severity = Severity.HARD,
        evaluation: Evaluation = Evaluation.POST_WRITE,
        message_template: str = "",
        source: str = "",
        citations: tuple = (),
    ):
        def deco(fn: Callable):
            self.registry._guard_dup(self.registry.rules, (ontology_id, name), "rule")
            self.registry.rules[(ontology_id, name)] = RuleDef(
                name=name, namespace=ontology_id, severity=severity,
                backing=backing, evaluation=evaluation, impl=fn,
                message_template=message_template, source=source, citations=tuple(citations),
            )
            return fn
        return deco

    # 槽位 4：受审计的业务动作
    def action(
        self,
        ontology_id: str,
        name: str,
        *,
        description: str = "",
        params: tuple = (),
        guards: tuple[str, ...] = (),
        post_rules: tuple[str, ...] = (),
        writes: tuple[str, ...] = (),
        validate_supported: bool = False,
        hil: Optional[HilPolicy] = None,
    ):
        def deco(fn: Callable):
            self.registry._guard_dup(self.registry.actions, (ontology_id, name), "action")
            self.registry.actions[(ontology_id, name)] = ActionDef(
                name=name, namespace=ontology_id, description=description, params=tuple(params),
                guards=guards, post_rules=post_rules, writes=writes,
                validate_supported=validate_supported, hil=hil, impl=fn,
            )
            return fn
        return deco
