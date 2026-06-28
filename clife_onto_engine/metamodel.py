"""元模型五要素 —— 内核与所有行业插件之间唯一的契约。

内核只理解这五种元类型。任何具体行业概念都是插件用这些元类型声明出来的实例，
本模块绝不包含行业词汇（CI 强制，见 scripts/check_kernel_purity.py）。

参见 docs/01-metamodel-and-plugin-spi.md。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class Severity(str, Enum):
    HARD = "hard"   # 违反即回滚
    SOFT = "soft"   # advisory，仅告警，不阻断


class Backing(str, Enum):
    DECLARATIVE = "declarative"  # 只看参数 / 用户上下文（轻、快）
    FUNCTION = "function"        # 读图谱 / 跨对象（重、准）


class Evaluation(str, Enum):
    PRE = "pre"               # guard：写入前
    POST_WRITE = "post_write"  # 全局不变式：写入后（需看到新状态）


class EdgeSemantics(str, Enum):
    """边的程序语义 —— 内核唯一需要理解的"关系含义"，用于多跳推理的终止判定。"""
    ROOT_CAUSE = "root_cause"   # 命中即可终止追溯
    HYPOTHESIS = "hypothesis"   # 继续追溯
    DERIVATION = "derivation"   # 派生关系


@dataclass(frozen=True)
class PropertySpec:
    name: str
    type: str
    unit: Optional[str] = None
    required: bool = False
    classification: Optional[str] = None  # 字段密级，如 confidential


@dataclass(frozen=True)
class ObjectType:
    name: str
    namespace: str                       # = ontology_id，内核据此隔离
    primary_key: str
    properties: tuple[PropertySpec, ...] = ()
    states: tuple[str, ...] = ()         # 生命周期状态机（可选）
    initial_state: Optional[str] = None
    source_required: bool = True


@dataclass(frozen=True)
class LinkType:
    name: str
    namespace: str
    from_type: str
    to_type: str
    cardinality: str = "N:N"
    edge_semantics: EdgeSemantics = EdgeSemantics.DERIVATION


@dataclass(frozen=True)
class FunctionDef:
    name: str
    namespace: str
    reads: tuple[str, ...] = ()
    impl: Optional[Callable] = None  # 由插件经 SPI 注册；side_effects 恒为 False


@dataclass(frozen=True)
class RuleDef:
    name: str
    namespace: str
    severity: Severity = Severity.HARD
    backing: Backing = Backing.DECLARATIVE
    evaluation: Evaluation = Evaluation.POST_WRITE
    impl: Optional[Callable] = None
    message_template: str = ""
    source: str = ""                  # 规则依据（标准/方法学/专家），治理出处
    citations: tuple[str, ...] = ()   # 引用来源，导出 OKF 时落 # Citations


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: str                        # string | number | list | object | ref(<Object>)
    required: bool = False
    description: str = ""


@dataclass(frozen=True)
class HilPolicy:
    """HIL 关口：满足条件则强制人工复核。predicate 由内核以裁决上下文调用。"""
    reviewer_role: str
    # predicate(confidence: float, touched_hard: bool) -> bool
    predicate: Callable[[float, bool], bool] = lambda confidence, touched_hard: False


@dataclass(frozen=True)
class ActionDef:
    name: str
    namespace: str
    description: str = ""               # 用于能力清单（喂给意图编译器）
    params: tuple[ParamSpec, ...] = ()  # 参数 schema：能力清单 + 意图校验
    guards: tuple[str, ...] = ()        # declarative 规则名，前置校验
    post_rules: tuple[str, ...] = ()    # 写后强制校验的规则名
    writes: tuple[str, ...] = ()        # 声明写入的对象类型
    validate_supported: bool = False
    hil: Optional[HilPolicy] = None
    impl: Optional[Callable] = None      # handler(ctx)，由插件注册
