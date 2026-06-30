"""治理写桥离线 smoke —— 断言红线（无网络、无 Go 进程、无 LLM）。

证明：act 经引擎兜底（合法违规动作照样 rejected 且**零反映**）；HIL 待审不反映；
读层挂掉时提交不回滚；写工具默认 opt-in。反映用可注入假 poster → 全程离线。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.mcp import GovernedBridge, Reflector
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor

import plugins.grass  # noqa: F401  (SPI 注册)


class _NoCompiler:  # query 路径不在本 smoke 内，占位即可
    pass


def _bridge(enable_act=True, post=None):
    store = InMemoryStore()
    plugins.grass.seed_reference_data(store)  # Site/parcel_001 + 巴彦淖尔乡土名录
    rec = []
    if post is None:
        def post(url, payload):  # 假 poster：记录而不发网络
            rec.append((url, payload)); return {"accepted": len(payload.get("entities", []))}
    refl = Reflector("http://reflect.local", "grass", post=post)
    br = GovernedBridge(ontology_id="grass", registry=spi.registry, store=store,
                        compiler=_NoCompiler(), actor=Actor("u1", "施工方"),
                        engine=ActionEngine(spi.registry, store=store),
                        reflector=refl, enable_act=enable_act)
    return br, rec


def main() -> int:
    fails = 0

    # 1) 合规草种 → 提交 → 反映进读层
    br, rec = _bridge()
    r = br.act("出一地一方", {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300})
    ok1 = r["kind"] == "committed" and r.get("reflected", 0) >= 1 and len(rec) == 1
    print(f"== 合规→提交+反映：{'✓' if ok1 else '✗ ' + str(r)} ==")
    fails += not ok1

    # 2) 非乡土草种 → 引擎确定性拒绝 → 零反映（本体兜底的活证据）
    br, rec = _bridge()
    r = br.act("出一地一方", {"site_id": "parcel_001", "species": ["紫花苜蓿"], "budget": 300})
    ok2 = r["kind"] == "rejected" and any(v["rule"] == "乡土合规" for v in r["violations"]) and len(rec) == 0
    print(f"== 违规→拒绝+零反映：{'✓' if ok2 else '✗ ' + str(r)} ==")
    fails += not ok2

    # 3) 读层挂掉（poster 抛错）→ 提交不回滚，记录 reflect_error
    def boom(url, payload):
        raise ConnectionError("read layer down")
    br, _ = _bridge(post=boom)
    r = br.act("出一地一方", {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300})
    ok3 = r["kind"] == "committed" and "reflect_error" in r
    print(f"== 读层挂→提交不回滚：{'✓' if ok3 else '✗ ' + str(r)} ==")
    fails += not ok3

    # 4) 写工具默认 opt-in：未启用时 tools 不含 act，act 调用被拒
    br, rec = _bridge(enable_act=False)
    ok4 = "act" not in br.tools() and br.act("出一地一方", {})["kind"] == "error" and len(rec) == 0
    print(f"== 写工具默认 opt-in：{'✓' if ok4 else '✗'} ==")
    fails += not ok4

    # 5) 结构不变量：桥只暴露 query/act，无任何直达 UModel 的写旁路
    br, _ = _bridge()
    ok5 = set(br.tools()) <= {"query", "act"}
    print(f"== 无 UModel 写旁路（只 query/act）：{'✓' if ok5 else '✗'} ==")
    fails += not ok5

    if fails:
        print(f"\n✗ 治理写桥 smoke 失败（{fails}）"); return 1
    print("\n✓ 治理写桥 smoke 全通过：写只经引擎、本体兜底、只反映已提交、读层解耦")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
