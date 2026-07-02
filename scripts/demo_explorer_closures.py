"""两条闭环·过程可溯 Explorer 演示（评审背书用）。

跑真实 ActionEngine 提交/拦截两条闭环，渲染运行时对象图 Explorer（自包含 HTML），
并打印每个动作的**审计血统**（决策 + 逐条规则 pass/violate + 证据 + 置信度）——
把"来源可查 / 过程可溯 / 结果可验"落成可看、可点、可查的实物。

运行：python scripts/demo_explorer_closures.py  → build/explorer/grass-closures.html
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clife_onto_engine.explorer import render
from clife_onto_engine.kernel import ActionEngine
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.sdk.context import Actor
from clife_onto_engine.trust.audit import AuditStore

import plugins.grass  # noqa: F401
from repl import seed  # 复用修复主干 + 参考数据 seed

_CYTO = (ROOT / "third-party" / "okf-visualizer" / "reference_agent" / "viewer"
         / "static" / "vendor" / "cytoscape.min.js").read_text(encoding="utf-8")


def _run(engine, tag, action, params, role):
    res = engine.execute("grass", action, params, Actor("demo", role),
                         schema_version="v1", ts="t")
    # 注意：ActionResult.committed 恒 True，须先判 decision 区分 pending_hil。
    decision = getattr(res, "decision", "rejected")
    if decision == "pending_hil":
        print(f"  ▶ {tag} → ⏸ pending_hil（转「{res.reviewer}」复核；置信 {res.confidence}）")
    elif decision == "committed":
        wrote = "、".join(dict.fromkeys(f"{t}:{k}" for t, k in res.written))  # 去重
        print(f"  ▶ {tag} → ✅ committed（写 {wrote}；置信 {res.confidence}）")
    else:  # StructuredRejection
        rules = "、".join(v.rule for v in res.violations)
        print(f"  ▶ {tag} → ⛔ rejected（{res.phase}·{rules}）")
    return res


def main() -> None:
    store = InMemoryStore()
    seed(store, "grass")   # Site parcel_001(盐碱) + 退化/修复主干 + GrassSpecies/名录/Standard
    store.put_object("Site", "parcel_hil",
                     {"parcel_id": "parcel_hil", "area_mu": 300, "region": "巴彦淖尔", "site_type": "盐碱"})
    audit = AuditStore()
    engine = ActionEngine(spi.registry, store=store, audit=audit)

    print("== 跑两条闭环（真实 ActionEngine·四类裁决）==")
    # A 草修·合规配比 → 提交（写 SeedPack + composed_of→GrassSpecies + Project）
    _run(engine, "A 草修·出一地一方(合规)", "出一地一方",
         {"site_id": "parcel_001", "species": ["碱茅", "星星草"],
          "composition": [{"species": "碱茅", "ratio": 70, "seeding_rate": 2.0},
                          {"species": "星星草", "ratio": 30, "seeding_rate": 1.5}],
          "method": "m_喷播", "budget": 300}, "施工方")
    # B 草易·快检 → 提交（写 QualityIndex + measured_by→Standard）
    _run(engine, "B 草易·快检评级(合规)", "快检评级",
         {"batch_id": "b1",
          "measurements": {"CP": 20, "NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.0}}, "养殖户")
    # C 乡土但立地不适配 → 拦截（披碱草不耐盐碱），演示"乡土 ≠ 立地适配"
    _run(engine, "C 草修·立地不适配", "出一地一方",
         {"site_id": "parcel_001", "species": ["披碱草"],
          "composition": [{"species": "披碱草", "ratio": 100, "seeding_rate": 2.0}],
          "budget": 300}, "施工方")
    # D 全合规但低置信 → 转 HIL 复核（结果可验：不确定不直接落地）
    _run(engine, "D 草修·低置信", "出一地一方",
         {"site_id": "parcel_hil", "species": ["碱茅"],
          "composition": [{"species": "碱茅", "ratio": 100, "seeding_rate": 2.0}],
          "budget": 300, "_confidence": 0.5}, "施工方")
    # E 草碳·碳汇核算 → 提交（写 CarbonReport + sequesters→Methodology，演示第三条闭环）
    _run(engine, "E 草碳·碳汇核算(合规)", "出碳汇核算报告",
         {"cp_id": "cp_001", "method_no": "CCER-GRASS-01"}, "碳汇开发")

    # ---- 过程可溯：审计血统 ----
    print("\n== 过程可溯·审计血统（每步决策 + 规则评估 + 证据）==")
    for s in audit.query("grass"):
        print(f"  · {s.action}｜{s.actor_role}｜决策 {s.decision}｜置信 {s.confidence}")
        for r in s.rules_evaluated:
            mark = "✓" if r.result == "pass" else "✗"
            msg = f" — {r.message}" if r.message else ""
            print(f"        {mark} {r.rule}（{r.backing}/{r.severity}）{msg}")
        if not s.rules_evaluated and s.decision != "rejected":
            print("        （硬规则全部通过 → 放行）")
        if s.evidence:
            print(f"        证据：{list(s.evidence)}")

    # ---- 自有展示：渲染运行时对象图 Explorer ----
    out_dir = ROOT / "build" / "explorer"
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render(spi.registry, store, "grass", cytoscape_js=_CYTO,
                  title="问草·两条闭环过程可溯")
    path = out_dir / "grass-closures.html"
    path.write_text(html, encoding="utf-8")
    nodes, edges = html.count('"otype"'), html.count('"source"')
    offline = "✓ 完全离线自包含" if 'src="https' not in html else "✗ 仍有外链"
    print(f"\n== Explorer：{nodes} 节点 · {edges} 边 · {offline} ==")
    print(f"   → {path.relative_to(ROOT)}（浏览器打开：点对象看属性/知识/遥测计划）")


if __name__ == "__main__":
    main()
