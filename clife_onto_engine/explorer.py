"""自有对象图 Explorer —— 把运行时对象图（GraphStore 的实例 + 关系）渲染成自包含 HTML。

本体 OS 的**自有展示**：不依赖 UModel Explorer 就能浏览治理对象图（类型上色 + 实例检视 + 图例）。
区别于 OKF viz（概念/schema 层），本模块渲染**实例层**（真实对象与关系）。

- **行业无关**（CI 强制）：只读 registry+store 渲染，不含行业词汇。
- **第三方无关**：cytoscape JS 由调用层注入（`cytoscape_js`）→ 内联即完全离线单文件；
  kernel 模块不 import、不读 third-party 路径（同 web.py 的工厂注入纪律）。
"""
from __future__ import annotations

import html
import json

# 稳定调色板：前若干类型取预置色，其余按类型名 hash 兜底（同名恒同色，不漂移）。
_PALETTE = ["#3b82f6", "#22c55e", "#a855f7", "#ef4444", "#f59e0b",
            "#06b6d4", "#ec4899", "#84cc16", "#6366f1", "#14b8a6"]
_NAME_HINTS = ("name", "display_name", "title", "label")


def _color(object_type: str, order: list[str]) -> str:
    if object_type in order and order.index(object_type) < len(_PALETTE):
        return _PALETTE[order.index(object_type)]
    return _PALETTE[sum(ord(c) for c in object_type) % len(_PALETTE)]


def _node_label(obj, key: str, row: dict) -> str:
    for h in _NAME_HINTS:
        if row.get(h):
            return str(row[h])
    pk = getattr(obj, "primary_key", None)
    return str(row.get(pk, key)) if pk else str(key)


def render(registry, store, ontology_id: str, *, cytoscape_js: str = "", title: str = "") -> str:
    """registry(+运行时 store) → 运行时对象图的自包含 HTML。"""
    types = [name for (ns, name) in registry.objects if ns == ontology_id]
    type_set = set(types)

    elements: list[dict] = []
    counts: dict[str, int] = {}
    for name in types:
        obj = registry.objects[(ontology_id, name)]
        for key, row in store.iter_objects(name):
            counts[name] = counts.get(name, 0) + 1
            elements.append({"data": {
                "id": f"{name}:{key}", "label": _node_label(obj, key, row),
                "otype": name, "props": row,
            }})
    n_edges = 0
    for e in getattr(store, "_edges", []):
        if e.from_type not in type_set or e.to_type not in type_set:
            continue
        n_edges += 1
        elements.append({"data": {
            "id": f"e{n_edges}:{e.link_type}", "label": e.link_type,
            "source": f"{e.from_type}:{e.from_key}", "target": f"{e.to_type}:{e.to_key}",
        }})

    color_map = {t: _color(t, types) for t in types if counts.get(t)}
    node_styles = "".join(
        f'cy.style().selector(\'node[otype="{html.escape(t)}"]\')'
        f'.style("background-color","{c}").update();'
        for t, c in color_map.items()
    )
    legend = "".join(
        f'<div class="lg"><span class="dot" style="background:{c}"></span>'
        f'{html.escape(t)} · {counts.get(t,0)}</div>'
        for t, c in color_map.items()
    )
    ttl = html.escape(title or f"对象图 Explorer · {ontology_id}")
    js_tag = f"<script>{cytoscape_js}</script>" if cytoscape_js else \
        '<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.28.1/dist/cytoscape.min.js"></script>'
    data_json = json.dumps(elements, ensure_ascii=False)

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>{ttl}</title>{js_tag}
<style>
 *{{box-sizing:border-box}} body{{margin:0;font:13px/1.6 -apple-system,system-ui,sans-serif;color:#0f172a}}
 #cy{{position:fixed;inset:0 320px 0 0;background:#f8fafc}}
 #side{{position:fixed;top:0;right:0;bottom:0;width:320px;border-left:1px solid #e2e8f0;
   background:#fff;padding:14px;overflow:auto}}
 h1{{font-size:15px;margin:0 0 10px}} .sub{{color:#64748b;margin-bottom:12px}}
 .lg{{display:flex;align-items:center;gap:7px}} .dot{{width:11px;height:11px;border-radius:50%;flex:0 0 auto}}
 #insp{{margin-top:14px;border-top:1px solid #e2e8f0;padding-top:10px}}
 table{{border-collapse:collapse;width:100%}} td{{border-bottom:1px solid #f1f5f9;padding:3px 4px;vertical-align:top}}
 td.k{{color:#64748b;white-space:nowrap;padding-right:8px}} .hint{{color:#94a3b8}}
</style></head><body>
<div id="cy"></div>
<div id="side">
 <h1>{ttl}</h1>
 <div class="sub">运行时对象图 · 点节点看属性</div>
 <div id="legend">{legend or '<span class="hint">（无实例）</span>'}</div>
 <div id="insp"><span class="hint">点一个节点查看其属性。</span></div>
</div>
<script>
 var ELS = {data_json};
 var cy = cytoscape({{
   container: document.getElementById('cy'), elements: ELS,
   style: [
     {{selector:'node', style:{{'label':'data(label)','font-size':10,'background-color':'#94a3b8',
        'text-valign':'center','color':'#0f172a','text-outline-width':2,'text-outline-color':'#f8fafc','width':22,'height':22}}}},
     {{selector:'edge', style:{{'label':'data(label)','font-size':8,'color':'#64748b','curve-style':'bezier',
        'target-arrow-shape':'triangle','line-color':'#cbd5e1','target-arrow-color':'#cbd5e1','width':1.5}}}}
   ],
   layout: {{name:'cose', animate:false}}
 }});
 {node_styles}
 function esc(s){{return String(s).replace(/[&<>]/g,function(c){{return {{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]}})}}
 cy.on('tap','node',function(evt){{
   var d = evt.target.data(); var p = d.props||{{}};
   var rows = Object.keys(p).map(function(k){{return '<tr><td class="k">'+esc(k)+'</td><td>'+esc(p[k])+'</td></tr>'}}).join('');
   document.getElementById('insp').innerHTML =
     '<div style="font-weight:600;margin-bottom:6px">'+esc(d.otype)+' · '+esc(d.label)+'</div>'+
     '<table>'+(rows||'<tr><td class="hint">（无属性）</td></tr>')+'</table>';
 }});
</script></body></html>"""
