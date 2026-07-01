"""租户数据接入 —— 声明式数据源 → 按本体 schema 校验 → 落库，产可审计报告。

`seed_reference_data` 是**代码里硬编码**的参考数据（demo/测试用）。生产落地不该改代码：
租户在 `tenants/<t>/tenant.yaml` **声明**数据源（文件/连接），入库时按 ObjectType schema
（必填字段、类型强制）校验、按主键落库，产出 `IngestReport`（载入数 / 逐行拒绝+原因 /
每对象完备度）——脏行不静默丢，留痕可审。这是"原型硬编码 → 产品数据接入"的接缝。

与行业无关：只认 registry 里的 ObjectType schema + 通用文件格式，无任何行业词（CI 强制）。
MVP 支持 csv / jsonl / json 文件源；真实 DB 源走薄 adapter（后续按需，不在此内联）。

    from clife_onto_engine.tenant import load_tenant
    report = load_tenant("tenants/mengcao/tenant.yaml", registry, store)
    print(report.summary())
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ObjectIngest:
    object_type: str
    loaded: int = 0
    rejected: list = field(default_factory=list)   # [(row_no, reason)]
    completeness: float = 1.0                       # 已声明属性的平均填充率


@dataclass
class IngestReport:
    tenant: str
    ontology: str
    objects: list = field(default_factory=list)     # [ObjectIngest]

    @property
    def total_loaded(self) -> int:
        return sum(o.loaded for o in self.objects)

    @property
    def total_rejected(self) -> int:
        return sum(len(o.rejected) for o in self.objects)

    def summary(self) -> str:
        head = f"租户 {self.tenant} · 本体 {self.ontology} · 载入 {self.total_loaded} · 拒绝 {self.total_rejected}"
        lines = [head]
        for o in self.objects:
            lines.append(f"  {o.object_type}: 载入 {o.loaded} · 拒绝 {len(o.rejected)} · 完备度 {o.completeness}")
            for row_no, reason in o.rejected:
                lines.append(f"      ✗ 第{row_no}行：{reason}")
        return "\n".join(lines)


def _split(s: str) -> list:
    return [x.strip() for x in s.replace("|", ";").split(";") if x.strip()]


def _coerce(value, typ: str):
    """按 schema 类型强制。空 → None；数字非法 → 抛 ValueError（上层记为拒绝行）。"""
    v = value.strip() if isinstance(value, str) else value
    if v == "" or v is None:
        return None
    if typ == "number":
        f = float(v)                       # 非法数字在此抛 ValueError
        return int(f) if f.is_integer() else f
    if typ == "list":
        return _split(v) if isinstance(v, str) else list(v)
    return v                               # string / enum / ref(...) / object → 原样


def _read_rows(path: Path, fmt: str) -> list:
    if fmt == "csv":
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    if fmt in ("jsonl", "ndjson"):
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    if fmt == "json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else [data]
    raise ValueError(f"未知数据格式: {fmt}")


def _resolve_key(row: dict, primary_key: str, key_template: Optional[str]):
    if key_template:                       # 形如 "{region}::{species}"，从行列拼主键
        try:
            return key_template.format(**row)
        except (KeyError, IndexError):
            return None
    val = row.get(primary_key)
    return val.strip() if isinstance(val, str) else val


def load_tenant(manifest_path, registry, store, *, base_dir=None) -> IngestReport:
    """读租户清单，逐源按本体 schema 校验落库。清单：{tenant, ontology, sources:[{object,file,format,key?}]}。"""
    manifest_path = Path(manifest_path)
    base = Path(base_dir) if base_dir else manifest_path.parent
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    ontology = manifest["ontology"]
    report = IngestReport(tenant=manifest.get("tenant", ""), ontology=ontology)

    for src in manifest.get("sources", []):
        ot_name = src["object"]
        oi = ObjectIngest(object_type=ot_name)
        obj_type = registry.objects.get((ontology, ot_name))
        if obj_type is None:
            oi.rejected.append((0, f"本体 {ontology} 未声明对象 {ot_name}"))
            report.objects.append(oi)
            continue

        rows = _read_rows(base / src["file"], src.get("format", "csv"))
        declared = obj_type.properties
        required = [p for p in declared if p.required]
        type_of = {p.name: p.type for p in declared}
        ratios = []
        for i, row in enumerate(rows, 1):
            key = _resolve_key(row, obj_type.primary_key, src.get("key"))
            if key in (None, ""):
                oi.rejected.append((i, f"主键缺失（{obj_type.primary_key} 或 key 模板未解析）"))
                continue
            data, bad = {}, None
            for col, raw in row.items():
                try:
                    data[col] = _coerce(raw, type_of.get(col, "string"))
                except (ValueError, TypeError):
                    bad = f"字段 {col}='{raw}' 无法转成 {type_of.get(col)}"
                    break
            if bad:
                oi.rejected.append((i, bad))
                continue
            missing = [p.name for p in required if data.get(p.name) in (None, "")]
            if missing:
                oi.rejected.append((i, f"缺必填字段 {missing}"))
                continue
            if declared:
                present = sum(1 for p in declared if data.get(p.name) not in (None, ""))
                ratios.append(present / len(declared))
            store.put_object(ot_name, key, data)
            oi.loaded += 1
        oi.completeness = round(sum(ratios) / len(ratios), 3) if ratios else 1.0
        report.objects.append(oi)
    return report
