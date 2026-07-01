"""本体版本化 —— 把某本体在某时刻的五要素定义快照成不可变、可寻址的版本。

治理化变更生命周期的地基（路线图 B/C 共享）：`schema_version` 从字符串标签，变成
一个**冻结的、可被 ActionEngine 直接执行**的版本快照。多版本共存、互不影响，
用于决策重放（replay.py）、规则变更影响分析、CQ 验收。

版本 = 一个只含该本体定义（+ 相关映射）的 Registry。五要素 def 是 frozen dataclass、
impl 是沙箱内纯函数，拷引用即不可变——快照后活 registry 的增改不回溯污染旧版本。

与行业无关（CI 强制）：只读复制 registry 结构，不含行业词汇。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .sdk.mapping import MappingRegistry
from .sdk.registry import Registry


def snapshot_ontology(registry: Registry, ontology_id: str, version: str) -> "OntologyVersion":
    """把 `registry` 中属于 ontology_id 的五要素定义 + 映射冻结成一个版本。"""
    snap = Registry()
    for (ns, name), obj in registry.objects.items():
        if ns == ontology_id:
            snap.objects[(ns, name)] = obj
    for (ns, name), lk in registry.links.items():
        if ns == ontology_id:
            snap.links[(ns, name)] = lk
    for (ns, name), fn in registry.functions.items():
        if ns == ontology_id:
            snap.functions[(ns, name)] = fn
    for (ns, name), r in registry.rules.items():
        if ns == ontology_id:
            snap.rules[(ns, name)] = r
    for (ns, name), a in registry.actions.items():
        if ns == ontology_id:
            snap.actions[(ns, name)] = a
    # 映射（槽位2）：function-backed 规则重放要用到，带上该 ns 的
    m = MappingRegistry()
    for key, om in registry.mappings.objects.items():
        if key[0] == ontology_id:
            m.objects[key] = om
    for key, lm in registry.mappings.links.items():
        if key[0] == ontology_id:
            m.links[key] = lm
    for key, tb in registry.mappings.telemetry.items():
        if key[0] == ontology_id:
            m.telemetry[key] = tb
    snap.mappings = m
    return OntologyVersion(ontology_id=ontology_id, version=version, registry=snap)


@dataclass(frozen=True)
class OntologyVersion:
    """一个本体在某版本的不可变快照。registry 具备 get_action/get_rule/get_function，
    可直接喂给 `ActionEngine(version.registry, store=...)` 执行——零新执行路径。"""
    ontology_id: str
    version: str
    registry: Registry


class OntologyVersionStore:
    """按 (ontology_id, version) 持有多个不可变版本。"""

    def __init__(self) -> None:
        self._versions: dict[tuple[str, str], OntologyVersion] = {}

    def put(self, v: OntologyVersion) -> None:
        self._versions[(v.ontology_id, v.version)] = v

    def get(self, ontology_id: str, version: str) -> Optional[OntologyVersion]:
        return self._versions.get((ontology_id, version))

    def list(self, ontology_id: Optional[str] = None) -> list[OntologyVersion]:
        vs = list(self._versions.values())
        return [v for v in vs if ontology_id is None or v.ontology_id == ontology_id]

    def snapshot(self, registry: Registry, ontology_id: str, version: str) -> OntologyVersion:
        """快照并入库，返回该版本。"""
        v = snapshot_ontology(registry, ontology_id, version)
        self.put(v)
        return v
