"""Plugin SPI 公开面 —— 插件唯一应当 import 的内核入口。

红线的物理体现：插件只 `from clife_onto_engine.sdk import ...`，
不直接 import 内核 kernel/ 内部实现。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..metamodel import (
    Backing,
    EdgeSemantics,
    Evaluation,
    HilPolicy,
    LinkType,
    ObjectType,
    ParamSpec,
    PropertySpec,
    Severity,
)
from .capability import Capability
from .context import Actor, ActionContext, Effect
from .errors import CapabilityError, OntoEngineError, RegistrationError, ResolutionError
from .mapping import (
    LinkMapping,
    MappingRegistry,
    Materialization,
    ObjectMapping,
    PhysicalBinding,
    SourceBinding,
)
from .registry import Registry, SPI

@dataclass(frozen=True)
class RuleResult:
    """规则 / guard 的返回值。passed=False 即违反。"""
    passed: bool
    message: str = ""
    suggestion: str = ""

    @classmethod
    def ok(cls) -> "RuleResult":
        return cls(passed=True)

    @classmethod
    def fail(cls, message: str = "", suggestion: str = "") -> "RuleResult":
        return cls(passed=False, message=message, suggestion=suggestion)


# 进程级默认 SPI 实例；插件用 `from clife_onto_engine.sdk import spi`。
# 测试可构造独立 SPI(Registry()) 注入引擎以隔离。
spi = SPI()

__all__ = [
    "spi",
    "SPI",
    "Registry",
    "RuleResult",
    "Actor",
    "ActionContext",
    "Capability",
    "Effect",
    "ObjectType",
    "LinkType",
    "ParamSpec",
    "PropertySpec",
    "Severity",
    "Backing",
    "Evaluation",
    "EdgeSemantics",
    "HilPolicy",
    "OntoEngineError",
    "RegistrationError",
    "ResolutionError",
    "CapabilityError",
    "MappingRegistry",
    "Materialization",
    "ObjectMapping",
    "LinkMapping",
    "PhysicalBinding",
    "SourceBinding",
]
