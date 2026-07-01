"""附着知识检索 —— 一次取"对象 + 它的知识"（多场景知识支持）。

吸收 Palantir（知识挂对象、同图一次取到）+ UModel（标准化知识类型），与我们已有的
强制知识（Rule）、派生知识（Function）并存。本模块只做**只读检索**；知识声明在插件
（槽位2 的 `knowledge:` 段，见 sdk/mapping.py）。行业无关（CI 强制）。
"""
from __future__ import annotations


def knowledge_for(registry, ontology_id: str, object_type: str) -> tuple:
    """取某对象类型的全部附着知识项（无绑定返回空）。"""
    return registry.mappings.get_knowledge(ontology_id, object_type)


def knowledge_of_kind(registry, ontology_id: str, object_type: str, kind: str) -> tuple:
    """按 kind 过滤（template/diagnostic/playbook/reference）。"""
    return tuple(k for k in knowledge_for(registry, ontology_id, object_type) if k.kind == kind)
