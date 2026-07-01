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


def load_into_memory(registry, memory, ontology_id: str, session_id: str,
                     *, kinds=None) -> int:
    """把本体的附着知识喂进四层记忆的 BACKGROUND 层，供 Session.ask 装配时按相关性注入 LLM。

    知识 → MemoryItem：content 为可读知识文本；tags=(对象类型, kind, 名称) 供相关性匹配；
    source="knowledge"；bound_entity=对象类型（供级联淘汰）。返回装载条数。
    """
    from .memory import Layer, MemoryItem  # 延迟导入避免环依赖

    n = 0
    for (ns, object_type), items in registry.mappings.knowledge.items():
        if ns != ontology_id:
            continue
        for item in items:
            if kinds is not None and item.kind not in kinds:
                continue
            memory.add(MemoryItem(
                id=f"kn:{ontology_id}:{object_type}:{item.name}",
                ontology_id=ontology_id, session_id=session_id, layer=Layer.BACKGROUND,
                content=f"[{item.kind}·{object_type}] {item.name}：{item.content}",
                tags=(object_type, item.kind, item.name), source="knowledge",
                bound_entity=object_type,
            ))
            n += 1
    return n
