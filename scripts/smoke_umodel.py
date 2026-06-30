"""UModel pack 离线 schema 校验（无网络、无 Go 进程，CI 友好）。

依据 vendored 的 UModel schema 规格（third-party/umodel-schemas/）做结构校验：
  1. 每个元素的 kind 必须在 manifest 已声明；
  2. metadata / spec 的**必填字段**必须齐全（含 extends 继承自 includes 的必填）。

这不是 UModel 权威校验器的完整复刻（权威校验在 umodel-server `validate`，sidecar 起时跑），
而是一道**离线确定性闸门**：导出器字段对不齐时早暴露。对齐 export_okf.py 的 _conformance 思路。

运行：  python scripts/smoke_umodel.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import yaml

from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.umodel import export_pack

import plugins.grass  # noqa: F401
import plugins.chili  # noqa: F401

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "third-party" / "umodel-schemas" / "schemas"


# ---- vendored schema 加载 ----------------------------------------------
def _spec_props(node: dict) -> dict:
    return ((node.get("versions") or [{}])[0].get("spec", {}).get("properties", {}))


def _load_schemas() -> tuple[dict, dict]:
    """返回 (kinds, includes)：kind→其 schema 的 versions[0].spec.properties；include 名→同结构。"""
    kinds, includes = {}, {}
    for p in (SCHEMA_DIR / "core").rglob("*.schema.yaml"):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        kinds[d["name"]] = _spec_props(d)
    for p in (SCHEMA_DIR / "includes").rglob("*.schema.yaml"):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        includes[d["name"]] = _spec_props(d)
    return kinds, includes


def _required_props(section_node: dict, includes: dict) -> set[str]:
    """某段（metadata/spec）的必填字段名：自身必填 + extends 继承的必填。"""
    req: set[str] = set()

    def _scan(props: dict) -> None:
        for name, v in (props or {}).items():
            if isinstance(v, dict) and (v.get("constraint") or {}).get("required"):
                req.add(name)

    _scan(section_node.get("properties"))
    for ext in section_node.get("extends", []) or []:
        inc = ext.split(":", 1)[0]
        if inc in includes:
            _scan(includes[inc])  # include 的 _spec_props 已是 properties 映射本身
    return req


def validate_pack(pack: pathlib.Path, kinds: dict, includes: dict) -> list[str]:
    errs: list[str] = []
    for y in sorted((pack / "umodel").rglob("*.yaml")):
        doc = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
        rel = y.relative_to(pack)
        kind = doc.get("kind")
        if kind not in kinds:
            errs.append(f"{rel}: 未知 kind '{kind}'")
            continue
        for top in ("schema", "metadata", "spec"):
            if top not in doc:
                errs.append(f"{rel}: 缺顶层段 '{top}'")
        spec_schema = kinds[kind]
        # metadata 必填（name/domain 等，含继承自 metadata include）
        for f in _required_props(spec_schema.get("metadata", {}), includes):
            if f not in (doc.get("metadata") or {}):
                errs.append(f"{rel}: metadata 缺必填 '{f}'")
        # spec 必填（含继承自 link/dataset include）
        for f in _required_props(spec_schema.get("spec", {}), includes):
            if f not in (doc.get("spec") or {}):
                errs.append(f"{rel}: spec 缺必填 '{f}'")
    return errs


def main() -> int:
    kinds, includes = _load_schemas()
    store = InMemoryStore()
    plugins.grass.seed_reference_data(store)

    failures = 0

    # 正例：grass / chili 导出 pack 应通过离线校验。
    for ns in ("grass", "chili"):
        out = ROOT / "build" / "umodel" / ns
        pack = export_pack(spi.registry, ns, str(out),
                           store=store if ns == "grass" else None, timestamp="2026-06-28")
        errs = validate_pack(pack, kinds, includes)
        n = len(list((pack / "umodel").rglob("*.yaml")))
        print(f"== {ns}: {n} 元素 · 离线校验 {'✓ 通过' if not errs else '✗ ' + str(errs)} ==")
        failures += bool(errs)

    # 反例：抹掉一个 entity_set 的 metadata.name，断言离线校验能拦截并定位。
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        bad = export_pack(spi.registry, "grass", tmp, store=store)
        victim = next((bad / "umodel" / "grass" / "entity_set").glob("*.yaml"))
        doc = yaml.safe_load(victim.read_text(encoding="utf-8"))
        doc["metadata"].pop("name", None)
        victim.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        errs = validate_pack(bad, kinds, includes)
        caught = any("metadata 缺必填 'name'" in e for e in errs)
        print(f"== 反例（删 metadata.name）：{'✓ 被拦截' if caught else '✗ 漏过'} → {[e for e in errs if 'name' in e][:1]} ==")
        failures += (not caught)

    if failures:
        print(f"\n✗ 离线校验失败（{failures}）")
        return 1
    print("\n✓ UModel pack 离线 schema 校验全通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
