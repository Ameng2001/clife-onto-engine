"""三范式训练集导出（对齐方案 §4.4）—— 把本体导成本体大模型的训练数据。

三范式（本体数据集三层）：
  1. **静态结构层**：实体 + 关系 Schema（"本体语法"：有哪些对象/关系/属性）→ 识别业务对象；
  2. **路径模板层**：核心多跳推理路径（沿关系链的模板）→ 识别推理路径与约束等式；
  3. **现象级实例层**：层级化推理轨迹（输入 → 规则评估 → 裁决 → 证据）→ 识别停止点与处置切换。

前两层从 registry 静态派生（schema + 关系链）；第三层从**审计快照**（真实裁决轨迹）派生。
产出结构化记录（可写 JSONL 供 SFT/CPT）。与 OKF（读/文档层）互补——OKF 供人读，本模块供训练。
行业无关（CI 强制）：只读 registry / 审计，不含任何行业词汇。
"""
from __future__ import annotations

import json
from pathlib import Path


# ---- 范式1：静态结构层 ------------------------------------------------
def export_static(registry, ontology_id: str) -> dict:
    objects = [
        {"type": name, "primary_key": o.primary_key,
         "fields": [p.name for p in o.properties],
         "states": list(o.states)}
        for (ns, name), o in sorted(registry.objects.items()) if ns == ontology_id
    ]
    links = [
        {"link": name, "from": lk.from_type, "to": lk.to_type,
         "semantics": lk.edge_semantics.value}
        for (ns, name), lk in sorted(registry.links.items()) if ns == ontology_id
    ]
    return {"paradigm": "static_structure", "objects": objects, "links": links}


# ---- 范式2：路径模板层 ------------------------------------------------
def _template(start: str, trail: list) -> str:
    s = start
    for h in trail:
        s += f" →{h['link']}→ {h['to']}"
    return s


def export_paths(registry, ontology_id: str, *, max_depth: int = 4, cap: int = 500) -> dict:
    """沿关系链枚举多跳路径模板（防环、限深、限量）。"""
    adj: dict = {}
    for (ns, name), lk in registry.links.items():
        if ns == ontology_id:
            adj.setdefault(lk.from_type, []).append((name, lk.to_type))
    out: list = []

    def dfs(start: str, cur: str, trail: list, seen: set) -> None:
        if len(trail) >= 2:                         # 至少 2 跳才算"推理路径"
            out.append({"start": start, "hops": list(trail), "template": _template(start, trail)})
        if len(trail) >= max_depth or len(out) >= cap:
            return
        for link_name, to in sorted(adj.get(cur, [])):
            if to in seen:                          # 防环
                continue
            dfs(start, to, trail + [{"link": link_name, "to": to}], seen | {to})

    for t in sorted({n for (ns, n) in registry.objects if ns == ontology_id}):
        if len(out) >= cap:
            break
        dfs(t, t, [], {t})
    return {"paradigm": "path_template", "paths": out[:cap]}


# ---- 范式3：现象级实例层 ----------------------------------------------
def export_phenomena(registry, ontology_id: str, audits) -> dict:
    """从审计快照派生推理轨迹：输入 → 规则评估(通过/违反) → 裁决 → 证据。"""
    traces = []
    for s in audits:
        if getattr(s, "ontology_id", None) != ontology_id:
            continue
        traces.append({
            "action": s.action, "actor_role": s.actor_role,
            "inputs": s.inputs_snapshot,
            "rules_evaluated": [{"rule": r.rule, "result": r.result,
                                 "severity": r.severity, "message": r.message}
                                for r in s.rules_evaluated],
            "decision": s.decision,                 # 停止点：committed / rejected / pending_hil
            "evidence": list(s.evidence),
        })
    return {"paradigm": "phenomenon_instance", "traces": traces}


# ---- 打包 + 写 JSONL --------------------------------------------------
def export_training(registry, ontology_id: str, *, audits=()) -> dict:
    return {
        "static": export_static(registry, ontology_id),
        "paths": export_paths(registry, ontology_id),
        "phenomena": export_phenomena(registry, ontology_id, audits),
    }


def write_training(bundle: dict, out_dir) -> dict:
    """把三范式各写一个 JSONL（每条一行结构化记录），返回每文件条数。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    files = {
        "static_structure.jsonl": (bundle["static"]["objects"], bundle["static"]["links"]),
        "path_template.jsonl": (bundle["paths"]["paths"],),
        "phenomenon_instance.jsonl": (bundle["phenomena"]["traces"],),
    }
    for fname, groups in files.items():
        rows = [r for g in groups for r in g]
        (out / fname).write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        counts[fname] = len(rows)
    return counts
