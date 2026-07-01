"""本体治理缺口审计（C1 运行时侧）—— 静态扫 registry，报"还没填完/治理缺口"。

studio-ontology 编译插件骨架时，function-backed 规则/Action 回写留 TODO(FDE)。本模块
提供一把静态尺子，上线前查：哪个 Action 没 handler、哪条规则引用悬空、哪条规则没出处、
哪个关系端点不存在——把"跑到才炸"提前到"静态可查"，补 OKF 的出处缺口审计。

两级：
  · blocking：结构性缺口，会在运行时解析失败/无法执行，必须修。
  · advisory：治理完整性缺口（如规则无出处），不阻断执行但治理不全。

与行业无关（CI 强制）：只读遍历 registry 结构，不含行业词汇。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Gap:
    kind: str          # action_no_handler | dangling_rule_ref | dangling_write |
                       # function_no_impl | dangling_link_endpoint | rule_no_source
    subject: str       # 具体定义名（形如 <ontology>.<name>）
    detail: str
    level: str         # blocking | advisory


@dataclass(frozen=True)
class GapReport:
    ontology_id: str
    blocking: tuple[Gap, ...] = ()
    advisory: tuple[Gap, ...] = ()

    @property
    def ok(self) -> bool:
        return len(self.blocking) == 0

    @property
    def summary(self) -> str:
        return (f"缺口审计 · {self.ontology_id}：blocking {len(self.blocking)} · "
                f"advisory {len(self.advisory)} · {'✓ 结构完整' if self.ok else '✗ 有结构缺口'}")


def audit_gaps(registry, ontology_id: str) -> GapReport:
    blocking: list[Gap] = []
    advisory: list[Gap] = []

    def q(name: str) -> str:
        return f"{ontology_id}.{name}"

    objects = {name for (ns, name) in registry.objects if ns == ontology_id}
    rules = {name for (ns, name) in registry.rules if ns == ontology_id}

    # Action：handler + 引用完整性
    for (ns, name), a in registry.actions.items():
        if ns != ontology_id:
            continue
        if a.impl is None:
            blocking.append(Gap("action_no_handler", q(name),
                                "Action 无 handler（impl=None），无法执行——待 FDE 回填", "blocking"))
        for r in tuple(a.guards) + tuple(a.post_rules):
            if r not in rules:
                blocking.append(Gap("dangling_rule_ref", q(name),
                                    f"引用未注册规则 '{r}'", "blocking"))
        for w in a.writes:
            if w not in objects:
                blocking.append(Gap("dangling_write", q(name),
                                    f"writes 指向未声明对象 '{w}'", "blocking"))

    # Function：impl
    for (ns, name), fn in registry.functions.items():
        if ns == ontology_id and fn.impl is None:
            blocking.append(Gap("function_no_impl", q(name),
                                "Function 无 impl，无法求值——待 FDE 回填", "blocking"))

    # Link：端点对象存在
    for (ns, name), lk in registry.links.items():
        if ns != ontology_id:
            continue
        for endpoint, role in ((lk.from_type, "from"), (lk.to_type, "to")):
            if endpoint not in objects:
                blocking.append(Gap("dangling_link_endpoint", q(name),
                                    f"{role} 端点对象 '{endpoint}' 未声明", "blocking"))

    # Rule：出处（治理完整性，advisory）
    for (ns, name), r in registry.rules.items():
        if ns == ontology_id and not r.source:
            advisory.append(Gap("rule_no_source", q(name),
                                "规则无 source 出处（治理文档缺口，补 OKF）", "advisory"))

    return GapReport(ontology_id=ontology_id,
                     blocking=tuple(blocking), advisory=tuple(advisory))
