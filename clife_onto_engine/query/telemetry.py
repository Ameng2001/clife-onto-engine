"""遥测 query-plan 生成 —— 本体 OS 自有"深读"的遥测侧（与 OQL 对象图读互补）。

据对象实例 + 声明的遥测绑定，把实例的 label 值**安全代入**生成器模板，产出**可执行查询计划**
（PromQL / ES DSL / SQL，id 已代入）。引擎**只产计划、不连后端、不执行**——与 UModel 同立场，
调用方（skill/agent/HTTP）拿计划自行打后端。天然离线、可测。

与 OQL 同纪律：不裸拼查询串——label 值先白名单校验（防注入），越界即拒。
与行业无关（CI 强制）：本模块只读绑定/实例，不含任何行业词汇。
"""
from __future__ import annotations

import re

# label 值白名单：字母数字 + 常见安全符（-_.:/ 空格中文）；元字符（{}"'`\等）一律拒，防注入。
_SAFE_LABEL = re.compile(r"^[\w\-.:/ 一-鿿]+$")


def _err(msg: str) -> dict:
    return {"ok": False, "error": msg}


def build_plan(registry, store, object_type: str, key: str, series_name: str,
               *, namespace: str) -> dict:
    """生成可执行查询计划（不执行）。

    成功 → {ok, provider, plan, resolved_labels, cost}；失败 → {ok: False, error}。
    """
    binding = registry.mappings.get_telemetry(namespace, object_type)
    if binding is None:
        return _err(f"未声明遥测绑定: {namespace}.{object_type}")
    series = next((s for s in binding.series if s.name == series_name), None)
    if series is None:
        avail = [s.name for s in binding.series]
        return _err(f"绑定无序列 '{series_name}'，可用: {avail}")
    row = store.get_object(object_type, key)
    if row is None:
        return _err(f"对象实例不存在: {object_type}/{key}")

    resolved: dict[str, str] = {}
    plan = series.template
    for placeholder, field in binding.labels.items():
        if field not in row or row[field] is None:
            return _err(f"实例缺 label 字段 '{field}'（占位 ${placeholder}）")
        val = str(row[field])
        if not _SAFE_LABEL.match(val):
            return _err(f"label 值含非法字符，拒绝代入（防注入）: {placeholder}={val!r}")
        resolved[placeholder] = val
        plan = plan.replace(f"${placeholder}", val)

    return {"ok": True, "provider": binding.provider, "kind": series.kind,
            "plan": plan, "resolved_labels": resolved,
            "cost": {"telemetry-plan": 1}}
