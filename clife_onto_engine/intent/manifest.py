"""能力清单 —— 把 Schema 变成 Agent/用户可见的能力清单（方法论：Schema→能力清单）。

从 registry 派生当前本体可用的 Action（名/描述/参数/写入）与对象/关系，喂给意图编译器。
与行业无关：清单内容由插件声明的 schema 决定，本模块不含行业词汇。
"""
from __future__ import annotations


def build_manifest(registry, ontology_id: str) -> dict:
    actions = []
    for (ns, name), a in registry.actions.items():
        if ns != ontology_id:
            continue
        actions.append({
            "name": name,
            "description": a.description,
            "params": [
                {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                for p in a.params
            ],
            "writes": list(a.writes),
        })
    objects = sorted(name for (ns, name) in registry.objects if ns == ontology_id)
    links = sorted(name for (ns, name) in registry.links if ns == ontology_id)
    return {"ontology_id": ontology_id, "actions": actions, "objects": objects, "links": links}


def render_manifest(m: dict) -> str:
    lines = [f"本体: {m['ontology_id']}", "可用动作(Action):"]
    for a in m["actions"]:
        ps = ", ".join(
            f"{p['name']}:{p['type']}{'(必填)' if p['required'] else ''}" for p in a["params"]
        )
        desc = f" —— {a['description']}" if a["description"] else ""
        lines.append(f"  - {a['name']}({ps}){desc}")
    lines.append("可用对象类型: " + ", ".join(m["objects"]))
    lines.append("可用关系类型: " + ", ".join(m["links"]))
    return "\n".join(lines)
