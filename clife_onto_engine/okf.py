"""OKF 导出器 —— 把本体（registry）渲染成符合 Open Knowledge Format v0.1 的知识包。

定位（关键，别混淆）：OKF 是**知识沉淀/文档层（读）**，与 OAG（受治理的写/执行）互补；
它**不表达、不运行**规则逻辑——规则的强制仍在引擎。本导出器把本体的对象/关系/规则/动作
渲染成"权威、可 git diff、可审计、可被别的 Agent 消费"的文档，承载规则的**出处与版本**，
落地"来源可查 + 配置即 PR"。详见 docs/03-okf-positioning.md。

OKF v0.1 约定：唯一必填 frontmatter 是 `type`；文件路径(去 .md)=概念 ID；md 链接=无类型有向边；
`index.md`/`log.md` 为保留文件；外部来源放 `# Citations`。消费者须容忍未知字段/类型/断链。

与行业无关：只读 registry 渲染，本模块不含行业词汇（CI 强制）。
"""
from __future__ import annotations

import pathlib
from typing import Optional

import yaml


def _write_concept(path: pathlib.Path, frontmatter: dict, body: str) -> None:
    fm = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm}\n---\n\n{body.rstrip()}\n", encoding="utf-8")


def _citations(cites: tuple) -> str:
    if not cites:
        return "\n# Citations\n\n_（治理审计：本规则尚无文档化依据，待补充标准/方法学）_"
    lines = "\n".join(f"[{i}] {c}" for i, c in enumerate(cites, 1))
    return f"\n# Citations\n\n{lines}"


def export_bundle(registry, ontology_id: str, out_dir: str,
                  *, timestamp: Optional[str] = None) -> pathlib.Path:
    root = pathlib.Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    index: dict[str, list[tuple[str, str]]] = {
        "Objects": [], "Links": [], "Functions": [], "Rules": [], "Actions": []}

    def fm_base(type_: str, title: str, desc: str = "") -> dict:
        d = {"type": type_, "title": title, "namespace": ontology_id}
        if desc:
            d["description"] = desc
        if timestamp:
            d["timestamp"] = timestamp
        return d

    # ---- Objects ----
    for (ns, name), o in registry.objects.items():
        if ns != ontology_id:
            continue
        fm = fm_base("ontology-object", name)
        fm["primary_key"] = o.primary_key
        if o.states:
            fm["states"] = list(o.states)
        props = "\n".join(
            f"- `{p.name}`: {p.type}{' (必填)' if p.required else ''}"
            f"{' · ' + p.unit if p.unit else ''}"
            f"{' · 密级:' + p.classification if p.classification else ''}"
            for p in o.properties
        ) or "_（无声明属性）_"
        _write_concept(root / "objects" / f"{name}.md", fm,
                       f"# {name}\n\n业务对象。主键 `{o.primary_key}`。\n\n## 属性\n\n{props}")
        index["Objects"].append((f"objects/{name}.md", name))

    # ---- Links ----
    for (ns, name), lk in registry.links.items():
        if ns != ontology_id:
            continue
        fm = fm_base("ontology-link", name)
        fm.update({"from": lk.from_type, "to": lk.to_type,
                   "edge_semantics": lk.edge_semantics.value, "cardinality": lk.cardinality})
        body = (f"# {name}\n\n关系：[{lk.from_type}](../objects/{lk.from_type}.md) "
                f"--{name}--> [{lk.to_type}](../objects/{lk.to_type}.md)\n\n"
                f"边语义 `{lk.edge_semantics.value}`（内核多跳推理的终止判定依据）。")
        _write_concept(root / "links" / f"{name}.md", fm, body)
        index["Links"].append((f"links/{name}.md", name))

    # ---- Functions ----
    for (ns, name), fdef in registry.functions.items():
        if ns != ontology_id:
            continue
        fm = fm_base("ontology-function", name)
        fm["reads"] = list(fdef.reads)
        reads = ", ".join(f"[{r}](../objects/{r}.md)" for r in fdef.reads) or "_（无）_"
        _write_concept(root / "functions" / f"{name}.md", fm,
                       f"# {name}\n\n只读派生量。读取：{reads}。")
        index["Functions"].append((f"functions/{name}.md", name))

    # ---- Rules（治理核心：出处 + 引用）----
    for (ns, name), r in registry.rules.items():
        if ns != ontology_id:
            continue
        fm = fm_base("ontology-rule", name, desc=r.message_template)
        fm.update({"severity": r.severity.value, "backing": r.backing.value,
                   "evaluation": r.evaluation.value})
        if r.source:
            fm["source"] = r.source
        body = (f"# {name}\n\n**裁决**：{r.severity.value}（{'违反即回滚' if r.severity.value=='hard' else 'advisory'}）"
                f" · **校验**：{r.backing.value} · **时机**：{r.evaluation.value}\n\n"
                f"拦截信息：{r.message_template or '_（未设）_'}\n\n"
                f"依据：{r.source or '_（待补充）_'}\n"
                f"{_citations(r.citations)}")
        _write_concept(root / "rules" / f"{name}.md", fm, body)
        index["Rules"].append((f"rules/{name}.md", name))

    # ---- Actions ----
    for (ns, name), a in registry.actions.items():
        if ns != ontology_id:
            continue
        fm = fm_base("ontology-action", name, desc=a.description)
        fm.update({"params": [{"name": p.name, "type": p.type, "required": p.required} for p in a.params],
                   "guards": list(a.guards), "post_rules": list(a.post_rules), "writes": list(a.writes)})
        if a.hil:
            fm["hil_reviewer"] = a.hil.reviewer_role
        guards = ", ".join(f"[{g}](../rules/{g}.md)" for g in a.guards) or "_（无）_"
        posts = ", ".join(f"[{p}](../rules/{p}.md)" for p in a.post_rules) or "_（无）_"
        writes = ", ".join(f"[{w}](../objects/{w}.md)" for w in a.writes) or "_（无）_"
        _write_concept(root / "actions" / f"{name}.md", fm,
                       f"# {name}\n\n{a.description}\n\n- 前置 guard：{guards}\n- 写后规则：{posts}\n"
                       f"- 写入对象：{writes}\n- HIL：{a.hil.reviewer_role if a.hil else '无'}")
        index["Actions"].append((f"actions/{name}.md", name))

    # ---- index.md（无 frontmatter；渐进式探索）----
    parts = [f"# 本体知识包 · {ontology_id}\n", "> 由 clife-onto-engine 从本体 registry 导出（OKF v0.1）。\n"]
    for section, items in index.items():
        if not items:
            continue
        parts.append(f"\n## {section}\n")
        for url, title in sorted(items):
            parts.append(f"* [{title}]({url})")
    (root / "index.md").write_text("\n".join(parts) + "\n", encoding="utf-8")

    return root
