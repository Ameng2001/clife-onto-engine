"""GraphStore SPI 与查询层。

内核通过 `GraphStore` 抽象与图后端交互，永不绑定具体实现：
  - `InMemoryGraphStore` —— dev / 测试后端（零依赖）
  - `NebulaGraphStore`   —— 生产后端（薄 adapter，见 nebula_store.py）

`QueryView` 在任意 GraphStore 之上叠加事务覆盖层（overlay），实现「写即可见」：
Action 期间 handler 暂存的对象/关系，本 handler 内与写后规则立即可读；回滚则丢弃覆盖层。

`search_around` 是 Search Around 关系算子（替代 JOIN，沿关系链跳跃，见 docs §7）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional, Protocol, runtime_checkable


# ---- 暂存操作（overlay 元素）------------------------------------------
@dataclass(frozen=True)
class StagedWrite:
    object_type: str
    key: str
    data: dict


@dataclass(frozen=True)
class StagedLink:
    link_type: str
    from_type: str
    from_key: str
    to_type: str
    to_key: str
    props: dict = field(default_factory=dict)


@dataclass(frozen=True)
class NeighborHit:
    node_type: str
    node_key: str
    node: dict
    edge_props: dict


# ---- GraphStore SPI ----------------------------------------------------
@runtime_checkable
class GraphStore(Protocol):
    """图后端契约。所有方法按 (object_type/link_type) 操作，租户隔离由实现保证
    （如 NebulaGraph 一个 ontology 一个 space）。"""

    def get_object(self, object_type: str, key: str) -> Optional[dict]: ...
    def iter_objects(self, object_type: str) -> Iterator[tuple[str, dict]]: ...
    def put_object(self, object_type: str, key: str, data: dict) -> None: ...
    def put_link(self, link: StagedLink) -> None: ...
    def delete_object(self, object_type: str, key: str) -> None: ...
    def delete_link(self, link: StagedLink) -> None: ...
    def search_around(
        self, object_type: str, key: str, link_type: str, *, direction: str = "out"
    ) -> list[NeighborHit]: ...


# ---- 内存实现（dev / 测试）--------------------------------------------
class InMemoryGraphStore:
    """已持久化的基底。节点按 (object_type,key)；边为列表。"""

    def __init__(self) -> None:
        self._nodes: dict[tuple[str, str], dict] = {}
        self._edges: list[StagedLink] = []

    def get_object(self, object_type: str, key: str) -> Optional[dict]:
        row = self._nodes.get((object_type, key))
        return dict(row) if row is not None else None

    def iter_objects(self, object_type: str) -> Iterator[tuple[str, dict]]:
        for (ot, k), row in self._nodes.items():
            if ot == object_type:
                yield k, dict(row)

    def put_object(self, object_type: str, key: str, data: dict) -> None:
        self._nodes[(object_type, key)] = dict(data)

    def put_link(self, link: StagedLink) -> None:
        self._edges.append(link)

    def delete_object(self, object_type: str, key: str) -> None:
        self._nodes.pop((object_type, key), None)

    def delete_link(self, link: StagedLink) -> None:
        self._edges = [
            e for e in self._edges
            if not (e.link_type == link.link_type and e.from_type == link.from_type
                    and e.from_key == link.from_key and e.to_type == link.to_type
                    and e.to_key == link.to_key)
        ]

    def search_around(self, object_type, key, link_type, *, direction="out") -> list[NeighborHit]:
        hits: list[NeighborHit] = []
        for e in self._edges:
            if e.link_type != link_type:
                continue
            if direction == "out" and (e.from_type, e.from_key) == (object_type, key):
                node = self.get_object(e.to_type, e.to_key) or {}
                hits.append(NeighborHit(e.to_type, e.to_key, node, dict(e.props)))
            elif direction == "in" and (e.to_type, e.to_key) == (object_type, key):
                node = self.get_object(e.from_type, e.from_key) or {}
                hits.append(NeighborHit(e.from_type, e.from_key, node, dict(e.props)))
        return hits


# 兼容别名：早期代码用 InMemoryStore。
InMemoryStore = InMemoryGraphStore


# ---- 事务覆盖视图（写即可见）------------------------------------------
class QueryView:
    """base ∪ overlay 的只读视图。overlay 含 StagedWrite / StagedLink。"""

    def __init__(self, base: GraphStore, overlay: list) -> None:
        self._base = base
        self._overlay = overlay

    def get(self, object_type: str, key: str) -> Optional[dict]:
        for op in reversed(self._overlay):  # 后写覆盖先写
            if isinstance(op, StagedWrite) and op.object_type == object_type and op.key == key:
                return dict(op.data)
        return self._base.get_object(object_type, key)

    def find(self, object_type: str, predicate) -> list[dict]:
        merged: dict[str, dict] = {}
        for k, row in self._base.iter_objects(object_type):
            merged[k] = row
        for op in self._overlay:
            if isinstance(op, StagedWrite) and op.object_type == object_type:
                merged[op.key] = dict(op.data)
        return [r for r in merged.values() if predicate(r)]

    def search_around(self, object_type, key, link_type, *, direction="out") -> list[NeighborHit]:
        hits = list(self._base.search_around(object_type, key, link_type, direction=direction))
        for op in self._overlay:  # 叠加本次暂存的边
            if not isinstance(op, StagedLink) or op.link_type != link_type:
                continue
            if direction == "out" and (op.from_type, op.from_key) == (object_type, key):
                hits.append(NeighborHit(op.to_type, op.to_key, self.get(op.to_type, op.to_key) or {}, dict(op.props)))
            elif direction == "in" and (op.to_type, op.to_key) == (object_type, key):
                hits.append(NeighborHit(op.from_type, op.from_key, self.get(op.from_type, op.from_key) or {}, dict(op.props)))
        return hits


__all__ = [
    "GraphStore", "InMemoryGraphStore", "InMemoryStore", "QueryView",
    "StagedWrite", "StagedLink", "NeighborHit",
]
