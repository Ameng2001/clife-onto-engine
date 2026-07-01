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
    objects = []
    for (ns, name), o in registry.objects.items():
        if ns != ontology_id:
            continue
        fields = [o.primary_key] + [p.name for p in o.properties if p.name != o.primary_key]
        objects.append({"name": name, "fields": fields})
    objects.sort(key=lambda x: x["name"])
    links = []
    for (ns, name), lk in registry.links.items():
        if ns != ontology_id:
            continue
        links.append({"name": name, "from": lk.from_type, "to": lk.to_type})
    links.sort(key=lambda x: x["name"])
    telemetry = []
    for (ns, ot), b in registry.mappings.telemetry.items():
        if ns != ontology_id:
            continue
        telemetry.append({"object": ot,
                          "series": [{"name": s.name, "kind": s.kind} for s in b.series]})
    telemetry.sort(key=lambda x: x["object"])
    return {"ontology_id": ontology_id, "actions": actions, "objects": objects,
            "links": links, "telemetry": telemetry}


def render_manifest(m: dict) -> str:
    lines = [f"本体: {m['ontology_id']}", "可用动作(Action):"]
    for a in m["actions"]:
        ps = ", ".join(
            f"{p['name']}:{p['type']}{'(必填)' if p['required'] else ''}" for p in a["params"]
        )
        desc = f" —— {a['description']}" if a["description"] else ""
        lines.append(f"  - {a['name']}({ps}){desc}")
    lines.append("可查对象类型及字段(用于 OQL 查询):")
    for o in m["objects"]:
        lines.append(f"  - {o['name']}(字段: {', '.join(o['fields'])})")
    lines.append("可用关系类型(用于多跳 Search Around):")
    for lk in m["links"]:
        lines.append(f"  - {lk['name']}: {lk['from']} → {lk['to']}")
    if m.get("telemetry"):
        lines.append("可观测遥测(用于'看某对象实例的指标/日志'):")
        for t in m["telemetry"]:
            series = ", ".join(f"{s['name']}({s['kind']})" for s in t["series"])
            lines.append(f"  - {t['object']}: {series}")
    return "\n".join(lines)
