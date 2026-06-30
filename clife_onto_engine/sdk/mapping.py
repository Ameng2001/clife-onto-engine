"""映射注册表（Plugin SPI 槽位 2）。

以**声明式**定义"对象→物理表/列、关系→连接键、物化策略"。是本体落地最硬的一环
（docs §4.12.3）。注册表本身与后端无关：物化引擎（NebulaGraph adapter / Ontop 虚拟）
读它决定怎么把字段绑定到对象、哪些进图、哪些虚拟兜底。

本模块只持有声明数据，不连任何库；与行业无关（CI 强制）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml  # PyYAML，成熟件

from .errors import RegistrationError


class Materialization(str, Enum):
    VIRTUAL = "virtual"        # OBDA 实时翻译为 SQL/图查询（明细/时序/交易，不进图）
    MATERIALIZED = "materialized"  # 实例化进图库（高频多跳推理子图）
    HYBRID = "hybrid"          # 主干物化 + 明细虚拟（推荐默认）


@dataclass(frozen=True)
class PhysicalBinding:
    store: str                 # postgis | clickhouse | milvus | nebula | ...
    table: str
    key: str                   # 业务主键列
    columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceBinding:
    """MDO 多源拼合：一个对象的属性来自多个源，按主键列向拼合（docs §4.12.8）。"""
    store: str
    table: str
    join: str                  # 与主键的连接键


@dataclass(frozen=True)
class ObjectMapping:
    object_type: str
    namespace: str
    materialization: Materialization
    primary: PhysicalBinding
    multi_source: tuple[SourceBinding, ...] = ()
    quality_gate: dict = field(default_factory=dict)   # 6 维质检阈值（插件设）


@dataclass(frozen=True)
class LinkMapping:
    link_type: str
    namespace: str
    materialization: Materialization
    from_key: str
    to_key: str
    via_table: Optional[str] = None    # 关系所在的连接表（虚拟时）
    store: Optional[str] = None


@dataclass(frozen=True)
class SeriesSpec:
    """一个遥测序列：名称 + provider + 生成器模板（含 $placeholder）。provider 在 series 级——
    同一对象的 metric 可走 prometheus、log 可走 elasticsearch。方言由模板作者负责。"""
    name: str
    template: str
    provider: str                      # prometheus | elasticsearch | sql
    kind: str = "metric"               # metric | log


@dataclass(frozen=True)
class TelemetryBinding:
    """对象 → 可观测后端的遥测绑定（与 ObjectMapping 同层；引擎只据此产查询计划，不执行）。

    labels: {占位名 -> 对象字段名}，build_plan 把对象实例该字段的值代入模板的 `$占位名`（跨 series 共享）。
    每个 series 自带 provider（metric/log 可不同后端）。
    """
    object_type: str
    namespace: str
    labels: dict                       # placeholder -> object_field
    series: tuple[SeriesSpec, ...] = ()


class MappingRegistry:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], ObjectMapping] = {}
        self.links: dict[tuple[str, str], LinkMapping] = {}
        self.telemetry: dict[tuple[str, str], TelemetryBinding] = {}

    def add_object(self, m: ObjectMapping) -> None:
        key = (m.namespace, m.object_type)
        if key in self.objects:
            raise RegistrationError(f"重复对象映射: {m.namespace}.{m.object_type}")
        self.objects[key] = m

    def add_link(self, m: LinkMapping) -> None:
        key = (m.namespace, m.link_type)
        if key in self.links:
            raise RegistrationError(f"重复关系映射: {m.namespace}.{m.link_type}")
        self.links[key] = m

    def add_telemetry(self, m: TelemetryBinding) -> None:
        key = (m.namespace, m.object_type)
        if key in self.telemetry:
            raise RegistrationError(f"重复遥测绑定: {m.namespace}.{m.object_type}")
        self.telemetry[key] = m

    def get_object(self, namespace: str, object_type: str) -> Optional[ObjectMapping]:
        return self.objects.get((namespace, object_type))

    def get_link(self, namespace: str, link_type: str) -> Optional[LinkMapping]:
        return self.links.get((namespace, link_type))

    def get_telemetry(self, namespace: str, object_type: str) -> Optional[TelemetryBinding]:
        return self.telemetry.get((namespace, object_type))

    # ---- YAML 加载（声明即文档；配置即 PR）----
    def load_yaml(self, namespace: str, path: str | Path) -> None:
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        for raw in doc.get("objects", []):
            self.add_object(_parse_object(namespace, raw))
        for raw in doc.get("links", []):
            self.add_link(_parse_link(namespace, raw))
        for raw in doc.get("telemetry", []):
            self.add_telemetry(_parse_telemetry(namespace, raw))


def _parse_object(namespace: str, raw: dict) -> ObjectMapping:
    phys = raw["physical"]
    primary = PhysicalBinding(
        store=phys["store"], table=phys["table"], key=phys["key"],
        columns=tuple(phys.get("columns", [])),
    )
    multi = tuple(
        SourceBinding(store=s["store"], table=s["table"], join=s["join"])
        for s in raw.get("multi_source", [])
    )
    return ObjectMapping(
        object_type=raw["object"], namespace=namespace,
        materialization=Materialization(raw.get("materialization", "hybrid")),
        primary=primary, multi_source=multi, quality_gate=raw.get("quality_gate", {}),
    )


def _parse_link(namespace: str, raw: dict) -> LinkMapping:
    return LinkMapping(
        link_type=raw["link"], namespace=namespace,
        materialization=Materialization(raw.get("materialization", "materialized")),
        from_key=raw["from_key"], to_key=raw["to_key"],
        via_table=raw.get("via_table"), store=raw.get("store"),
    )


def _parse_telemetry(namespace: str, raw: dict) -> TelemetryBinding:
    default_provider = raw.get("provider")   # 绑定级默认 provider（可选），series 可覆盖
    series = tuple(
        SeriesSpec(name=s["name"], template=s["template"],
                   provider=s.get("provider", default_provider),
                   kind=s.get("kind", "metric"))
        for s in raw.get("series", [])
    )
    return TelemetryBinding(
        object_type=raw["object"], namespace=namespace,
        labels=dict(raw.get("labels", {})), series=series,
    )
