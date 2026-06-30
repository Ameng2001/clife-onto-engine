"""UModel 导出器 —— 把本体（registry）编译成 UModel（Alibaba UnifiedModel）model pack。

定位（关键，别混淆）：UModel 是本引擎之上的**只读语义层**（Web Explorer / SPL 受控读 /
MCP 读工具），与 OAG（受治理的写/执行）互补。本导出器把五要素里**可读半区**
（Object / Link / 物理映射 / 运行时实例）渲染成 UModel 可装载的 YAML pack + 实例 JSON，
让治理对象图能被浏览、被 SPL 查、被任何 MCP agent 读取。

**治理写半区（Function / Rule / Action）刻意不映射**：UModel 不提供受治理的写，
治理永远留在引擎（guard→写后规则→回滚→审计）。Rule 至多作只读元数据，不作 enforcement。
详见 docs/04-umodel-interop.md。

与行业无关：只读 registry 渲染，本模块不含任何行业词汇（CI 强制）。
依赖：仅 PyYAML（已在 requirements）。UModel 本身以容器 sidecar 形态运行，不被本模块 import。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Optional

import yaml

# 钉定的 schema 标识（对齐 third-party/umodel-schemas/，见 PROVENANCE）。
_SCHEMA = {"url": "umodel.aliyun.com", "version": "v0.1.0"}

# 运行时实例的观测时间窗（UModel EntityStore 必填，int64 epoch）。
# 用确定性常量（非 wall-clock）→ 导出可重放；__to__ 设到 2100 年保证实例不被 TTL 过期。
_OBSERVED_FROM = 1704067200   # 2024-01-01Z
_OBSERVED_TO = 4102444800     # 2100-01-01Z

# 五要素属性类型 → UModel field_spec 类型（string/integer/float/boolean/time/json_object/json_array）。
_TYPE_MAP = {
    "number": "float", "float": "float", "integer": "integer", "int": "integer",
    "boolean": "boolean", "bool": "boolean", "string": "string", "enum": "string",
    "list": "json_array", "object": "json_object",
}
# 'name' 候选字段（取作 entity_set 的 name_fields，供 Explorer 展示）。
_NAME_HINTS = ("name", "display_name", "title")


def _field_type(t: str) -> str:
    base = t.split("(", 1)[0].strip().lower()  # ref(Site) → ref → string 兜底
    return _TYPE_MAP.get(base, "string")


def _meta(name: str, domain: str) -> dict:
    return {"name": name, "domain": domain,
            "display_name": {"en_us": name, "zh_cn": name}}


def _dump_yaml(path: pathlib.Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _qualified(domain: str, type_name: str) -> str:
    return f"{domain}.{type_name}"


def _eid(domain: str, type_name: str, key: str) -> str:
    """确定性 32 位小写 hex 实例 ID（UModel `__entity_id__` 格式要求）。

    由 (domain, 对象类型, 业务主键值) 的 md5 派生 → 同一自然键恒得同一 ID，
    保证关系两端引用与实例 ID 一致、且导出可重放。
    """
    return hashlib.md5(f"{domain}:{type_name}:{key}".encode("utf-8")).hexdigest()


def export_pack(registry, ontology_id: str, out_dir: str,
                *, store=None, timestamp: Optional[str] = None) -> pathlib.Path:
    """registry（+ 可选运行时 store）→ UModel model pack 目录。

    domain 与 workspace 名均取 ontology_id（延续 space-per-ontology 隔离）。
    产物布局对齐 UModel examples：
        <out_dir>/umodel/<domain>/{entity_set,link/entity_set_link,storage}/*.yaml
        <out_dir>/sample-data/{entities,relations}.json
    """
    domain = ontology_id
    root = pathlib.Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    um = root / "umodel" / domain

    # 本 ontology 的对象名集合（用于过滤关系与实例，保证引用闭合）。
    object_names = {name for (ns, name) in registry.objects if ns == ontology_id}

    # ---- ObjectType → entity_set ----------------------------------------
    for (ns, name), o in registry.objects.items():
        if ns != ontology_id:
            continue
        # 主键必须是一个存在的 field：properties 里没有就补一个 string 主键字段。
        fields = []
        seen = set()
        if o.primary_key not in {p.name for p in o.properties}:
            fields.append({"name": o.primary_key, "type": "string"})
            seen.add(o.primary_key)
        for p in o.properties:
            if p.name in seen:
                continue
            seen.add(p.name)
            f = {"name": p.name, "type": _field_type(p.type)}
            if p.unit:
                f["description"] = {"zh_cn": f"单位：{p.unit}", "en_us": f"unit: {p.unit}"}
            fields.append(f)
        name_field = next((p.name for p in o.properties if p.name in _NAME_HINTS),
                          o.primary_key)
        spec = {
            "fields": fields,
            "primary_key_fields": [o.primary_key],
            "id_generator": o.primary_key,
            "name_fields": [name_field],
            "ordered_fields": [f["name"] for f in fields],
        }
        if o.states:
            # 生命周期状态作为只读元数据注解（非 enforcement）。
            spec["tags"] = {"states": list(o.states), "initial_state": o.initial_state or ""}
        _dump_yaml(um / "entity_set" / f"{name}.yaml", {
            "kind": "entity_set", "schema": dict(_SCHEMA),
            "metadata": _meta(_qualified(domain, name), domain), "spec": spec,
        })

    # ---- LinkType → entity_set_link -------------------------------------
    for (ns, name), lk in registry.links.items():
        if ns != ontology_id:
            continue
        ref = lambda tn: {"domain": domain, "kind": "entity_set",
                          "name": _qualified(domain, tn)}
        meta = _meta(_qualified(domain, name), domain)
        # 边的程序语义作为只读元数据（内核多跳推理才 enforce，UModel 仅展示）。
        meta["description"] = {
            "zh_cn": f"边语义：{lk.edge_semantics.value}（仅展示，治理终止判定在引擎内）",
            "en_us": f"edge semantics: {lk.edge_semantics.value} (display-only)",
        }
        _dump_yaml(um / "link" / "entity_set_link" / f"{name}.yaml", {
            "kind": "entity_set_link", "schema": dict(_SCHEMA), "metadata": meta,
            "spec": {"src": ref(lk.from_type), "dest": ref(lk.to_type),
                     "entity_link_type": name},
        })

    # ---- 映射注册表（槽位2）→ external_storage（承载后端可见性）----------
    # UModel 原生链是 entity_set→dataset→storage；我们的映射是 object→物理表（无中间数据集），
    # 故先把每个物理落点导成 external_storage（type+name 即合规），把表/列/物化策略落 tags。
    # object↔storage 的 link（entity_source_link，experimental）留作后续。
    seen_storage: set[str] = set()

    def _emit_storage(store_kind: str, table: str, tags: dict) -> None:
        sname = f"{domain}.storage.{store_kind}.{table}"
        if sname in seen_storage:
            return
        seen_storage.add(sname)
        _dump_yaml(um / "storage" / f"{store_kind}.{table}.yaml", {
            "kind": "external_storage", "schema": dict(_SCHEMA),
            "metadata": _meta(sname, domain),
            "spec": {"type": store_kind, "name": table,
                     "tags": {k: v for k, v in tags.items() if v}},
        })

    for (ns, otype), m in registry.mappings.objects.items():
        if ns != ontology_id:
            continue
        _emit_storage(m.primary.store, m.primary.table, {
            "object": otype, "materialization": m.materialization.value,
            "key": m.primary.key, "columns": ", ".join(m.primary.columns),
        })
        for src in m.multi_source:
            _emit_storage(src.store, src.table,
                          {"object": otype, "join": src.join, "role": "multi_source"})

    # ---- 运行时实例 → sample-data/entities.json · relations.json --------
    entities, relations = [], []
    if store is not None:
        for name in sorted(object_names):
            for key, row in store.iter_objects(name):
                rec = {"__domain__": domain, "__entity_type__": _qualified(domain, name),
                       "__entity_id__": _eid(domain, name, key), "__category__": "entity",
                       "__method__": "Update",
                       "__first_observed_time__": _OBSERVED_FROM,
                       "__last_observed_time__": _OBSERVED_TO}
                rec.update(row)  # 业务字段（自然主键仍在，供 SPL project/过滤）
                entities.append(rec)
        for e in getattr(store, "_edges", []):
            if e.from_type not in object_names or e.to_type not in object_names:
                continue
            relations.append({
                "__src_domain__": domain, "__src_entity_type__": _qualified(domain, e.from_type),
                "__src_entity_id__": _eid(domain, e.from_type, e.from_key),
                "__dest_domain__": domain, "__dest_entity_type__": _qualified(domain, e.to_type),
                "__dest_entity_id__": _eid(domain, e.to_type, e.to_key),
                "__relation_type__": e.link_type, "__category__": "entity_link",
                "__method__": "Update",
                "__first_observed_time__": _OBSERVED_FROM,
                "__last_observed_time__": _OBSERVED_TO, **(e.props or {}),
            })

    sd = root / "sample-data"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "entities.json").write_text(
        json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8")
    (sd / "relations.json").write_text(
        json.dumps(relations, ensure_ascii=False, indent=2), encoding="utf-8")

    return root
