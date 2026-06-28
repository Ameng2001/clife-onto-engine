"""Capability —— 插件代码唯一可见的受限能力句柄（就是传给 handler/rule/function 的 `ctx`）。

把"受限"从约定变成约束（docs §4.3）。在进程内做四层真校验：

  1. 租户/类型作用域：只能访问**本 ontology_id 内已声明**的对象/关系；越权抛 CapabilityError。
     —— 跨租户结构上不可能（registry 按 (namespace,name) 索引，只查本 ns）。
  2. 写声明强制：stage_write 只允许当前 Action 在 `writes` 里声明过的对象类型。
  3. Function 最小权限：call_function 期间，读取被限制在该 Function 声明的 `reads` 集内。
  4. 能力收窄：内核内部（changeset/effects/view/base store）不在本门面暴露；下层 ActionContext
     以名称改写私有持有，杜绝顺手 `ctx._view._base.put_object()` 直接写库。

诚实边界：纯进程内无法绝对阻止 `import socket` 之类逃逸——那由
`scripts/check_plugin_capabilities.py`（静态能力 CI）兜底；需对不可信第三方插件做强隔离时，
再加进程/WASM 边界（决策点 3 的另一档）。
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from ..query import NeighborHit, StagedLink, StagedWrite
from .context import ActionContext, Effect
from .errors import CapabilityError


class Capability:
    def __init__(self, ctx: ActionContext, registry, action_def=None) -> None:
        self.__ctx = ctx
        self.__reg = registry
        self.__action = action_def
        self.__ns = ctx.ontology_id
        self.__read_scope: Optional[set] = None  # None=本租户全部已声明类型；set=Function 限定

    # ---- 输入（只读副本）----
    @property
    def params(self) -> dict:
        return dict(self.__ctx.params)

    @property
    def actor(self):
        return self.__ctx.actor

    @property
    def ontology_id(self) -> str:
        return self.__ns

    # ---- 作用域校验 ----
    def __check_object(self, t: str) -> None:
        if (self.__ns, t) not in self.__reg.objects:
            raise CapabilityError(f"越权/未声明对象类型: {self.__ns}.{t}")
        if self.__read_scope is not None and t not in self.__read_scope:
            raise CapabilityError(
                f"最小权限: 当前 Function 仅可读 {sorted(self.__read_scope)}，越权读 {t}"
            )

    def __check_link(self, lt: str) -> None:
        if (self.__ns, lt) not in self.__reg.links:
            raise CapabilityError(f"越权/未声明关系类型: {self.__ns}.{lt}")

    # ---- 只读查询 ----
    def get(self, object_type: str, key: str) -> Optional[dict]:
        self.__check_object(object_type)
        return self.__ctx.view.get(object_type, key)

    def find(self, object_type: str, predicate: Callable[[dict], bool]) -> list[dict]:
        self.__check_object(object_type)
        return self.__ctx.view.find(object_type, predicate)

    def search_around(self, object_type: str, key: str, link_type: str,
                      *, direction: str = "out") -> list[NeighborHit]:
        self.__check_object(object_type)
        self.__check_link(link_type)
        return self.__ctx.view.search_around(object_type, key, link_type, direction=direction)

    def call_function(self, name: str) -> Any:
        fdef = self.__reg.get_function(self.__ns, name)
        prev = self.__read_scope
        self.__read_scope = set(fdef.reads)  # 最小权限：仅可读声明的 reads
        try:
            return fdef.impl(self)
        finally:
            self.__read_scope = prev

    # ---- 暂存写入（进 overlay，commit 才落库）----
    def stage_write(self, object_type: str, key: str, data: dict) -> None:
        self.__check_object(object_type)
        if self.__action is not None and object_type not in self.__action.writes:
            raise CapabilityError(
                f"未声明写入: Action {self.__action.name} 的 writes 不含 {object_type}"
            )
        self.__ctx._stage(StagedWrite(object_type=object_type, key=key, data=dict(data)))

    def stage_link(self, link_type: str, from_type: str, from_key: str,
                   to_type: str, to_key: str, **props) -> None:
        self.__check_link(link_type)
        self.__check_object(from_type)
        self.__check_object(to_type)
        self.__ctx._stage(StagedLink(
            link_type=link_type, from_type=from_type, from_key=from_key,
            to_type=to_type, to_key=to_key, props=dict(props),
        ))

    # ---- 副作用 / 信任元数据 ----
    def emit_effect(self, type: str, *, on: Optional[str] = None, **payload) -> None:
        self.__ctx._add_effect(Effect(type=type, on=on, payload=dict(payload)))

    def set_confidence(self, value: float) -> None:
        self.__ctx._set_confidence(value)

    def add_evidence(self, **kv) -> None:
        self.__ctx._add_evidence(dict(kv))
