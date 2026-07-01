"""延迟基准 —— 量 `Session.ask` 治理管道的端到端延迟（记忆接地→路由→查/做→回滚/审计）。

离线（默认，脚本编译器）：量的是**引擎侧管道**延迟（不含 LLM），确定性、可回归——部署容量规划的下界。
真 Qwen 延迟由网络/模型主导（通常几百 ms~数秒），量它直接 time 一次 serve `/ask` 即可（见 docs/06）。

    python scripts/bench.py [N]      # 默认每类 200 次
"""
from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.query.oql import Cond, OQLQuery
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.session import Session
from clife_onto_engine.tenant import load_tenant

import plugins.grass  # noqa: F401
from scripts.e2e_corpus import CompiledIntent


class _Fixed:
    """固定意图编译器（隔离 LLM，只量引擎管道）。"""
    def __init__(self, ci): self._ci = ci
    def compile(self, *a, **k): return self._ci


def _pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))]


def _bench(name, session, utterance, n):
    lat = []
    for _ in range(n):
        t0 = time.perf_counter()
        session.ask(utterance)
        lat.append((time.perf_counter() - t0) * 1000)
    ms = lambda p: f"{_pct(lat, p):.3f}"
    print(f"  {name:10s} n={n}  p50={ms(0.50)}ms  p95={ms(0.95)}ms  p99={ms(0.99)}ms  mean={sum(lat)/len(lat):.3f}ms")


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    store = InMemoryStore()
    rep = load_tenant(ROOT / "tenants" / "mengcao" / "tenant.yaml", spi.registry, store)
    print(f"== 延迟基准（Session.ask 管道，离线脚本编译器）· 租户数据 {rep.total_loaded} 对象 · N={n} ==")

    read_ci = CompiledIntent("query", confidence=0.9,
        oql=OQLQuery(namespace="grass", start="Site", where=(Cond("region", "eq", "巴彦淖尔"),)))
    write_ci = CompiledIntent("action", action="出一地一方", confidence=0.9,
        params={"site_id": "parcel_001", "species": ["碱茅"], "budget": 300})
    reject_ci = CompiledIntent("action", action="出一地一方", confidence=0.9,
        params={"site_id": "parcel_001", "species": ["紫花苜蓿"], "budget": 300})

    def sess(ci):
        return Session(ontology_id="grass", registry=spi.registry, store=store,
                       compiler=_Fixed(ci), actor=Actor("u", "施工方"),
                       schema_version="grass@0.1.0", load_knowledge=True)

    _bench("读·查询", sess(read_ci), "巴彦淖尔有哪些地块", n)
    _bench("写·提交", sess(write_ci), "给 parcel_001 出方案用碱茅预算300", n)
    _bench("写·拒绝", sess(reject_ci), "给 parcel_001 出方案用紫花苜蓿预算300", n)
    print("\n注：以上为引擎管道延迟（不含 LLM）。真 Qwen 端到端延迟由模型主导，见 docs/06 部署 runbook。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
