"""租户数据接入 harness —— 声明式加载 tenants/<t> → 报告 → 在真数据上跑 CQ 验收。

证明"原型硬编码 → 产品数据接入"的接缝可用：不改插件代码，从租户清单把数据按 schema 校验落库，
再用该本体的 CQ 套件在**加载的租户数据**（而非 seed_reference_data）上跑 pass/fail。

    python scripts/tenant_load.py                 # 默认租户 mengcao
    python scripts/tenant_load.py tenants/<t>/tenant.yaml
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.cq import run_cq_suite
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.tenant import load_tenant

import plugins.grass  # noqa: F401  （注册 grass 本体 + CQ 套件）
from plugins.grass.cq import CQ_SUITE


def main() -> int:
    manifest = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "tenants" / "mengcao" / "tenant.yaml")
    print(f"== 租户数据接入：{manifest} ==")

    store = InMemoryStore()
    report = load_tenant(manifest, spi.registry, store)
    print(report.summary())

    # 在加载的真实（此处样例）租户数据上跑 CQ 验收 —— 不是 seed，是 tenant.yaml 声明的数据
    print("\n== CQ 验收（跑在加载的租户数据上）==")
    cq = run_cq_suite(CQ_SUITE, spi.registry, store=store)
    for r in cq.results:
        print(f"  {'✓' if r.passed else '✗'} {r.name}" + ("" if r.passed else f" · {r.detail}"))
    print(f"\n== 接入 {report.total_loaded} 对象（拒绝 {report.total_rejected}）· CQ {cq.passed}/{cq.total} ==")
    return 0 if (report.total_loaded > 0 and cq.failed == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
