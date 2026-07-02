"""草业插件·CQ 验收集（Plugin SPI 槽位 7）—— 本体能力验证问题。

声明"这个本体该会做什么、做对什么、查得到什么"，供 run_cq_suite 对某版本跑 pass/fail。
CQ 是数据声明，内核只跑不含它（换行业换套件、零改内核）。
"""
from __future__ import annotations

from clife_onto_engine.cq import ActionCQ, QueryCQ
from clife_onto_engine.query.oql import Cond, OQLQuery

ONTOLOGY = "grass"

CQ_SUITE = (
    # 会做且做得对：合规乡土草种应出方案（commit）
    ActionCQ("合规草种出方案", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
             actor_role="施工方", expect="commit"),
    # 本体兜底：非乡土草种应被「乡土合规」拦
    ActionCQ("非乡土草种被拦", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["紫花苜蓿"], "budget": 300},
             actor_role="施工方", expect="reject", expect_rule="乡土合规"),
    # 权限：越权角色应被「角色权限」拦
    ActionCQ("越权角色被拦", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["碱茅"], "budget": 300},
             actor_role="游客", expect="reject", expect_rule="角色权限"),
    # 配比合规：Σ比例=100% ∧ 播量∈区间 → 出方案（commit）
    ActionCQ("合规配比出方案", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["碱茅", "星星草"],
              "composition": [{"species": "碱茅", "ratio": 70, "seeding_rate": 2.0},
                              {"species": "星星草", "ratio": 30, "seeding_rate": 1.5}],
              "budget": 300},
             actor_role="施工方", expect="commit"),
    # 本体兜底：混播比例合计≠100% 应被「混播配比合规」拦
    ActionCQ("配比不足被拦", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["碱茅", "星星草"],
              "composition": [{"species": "碱茅", "ratio": 60, "seeding_rate": 2.0},
                              {"species": "星星草", "ratio": 30, "seeding_rate": 1.5}],
              "budget": 300},
             actor_role="施工方", expect="reject", expect_rule="混播配比合规"),
    # 本体兜底：播量越出品种区间应被「混播配比合规」拦（碱茅上限 2.5）
    ActionCQ("播量越界被拦", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["碱茅"],
              "composition": [{"species": "碱茅", "ratio": 100, "seeding_rate": 5.0}],
              "budget": 300},
             actor_role="施工方", expect="reject", expect_rule="混播配比合规"),
    # 本体兜底：乡土但不适配立地应被「立地适配」拦（披碱草是巴彦淖尔乡土、却不耐盐碱）
    ActionCQ("乡土但立地不适配被拦", ONTOLOGY, "出一地一方",
             {"site_id": "parcel_001", "species": ["披碱草"],
              "composition": [{"species": "披碱草", "ratio": 100, "seeding_rate": 2.0}],
              "budget": 300},
             actor_role="施工方", expect="reject", expect_rule="立地适配"),
    # 会查：某盟市应查得到地块
    QueryCQ("某区域有地块", ONTOLOGY,
            OQLQuery(namespace=ONTOLOGY, start="Site",
                     where=(Cond("region", "eq", "巴彦淖尔"),)),
            min_rows=1),

    # ---- 闭环 B · 草易·快检评级（B1–B3：品质对象层 + 挂依据标准）----------
    # commit 通过即证明 B1–B3 接线正确：validate 干跑会执行 handler 的
    # stage_write("QualityIndex") 与 stage_link("measured_by"→Standard)，
    # 若对象/关系/writes 未声明会抛 CapabilityError 使 CQ 失败。
    ActionCQ("合规草样出评级", ONTOLOGY, "快检评级",
             {"batch_id": "b1",
              "measurements": {"CP": 20, "NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.0}},
             actor_role="养殖户", expect="commit"),
    # 本体兜底：霉变超标应被「霉变拦截」拦（治理不因结构化改造被绕过）
    ActionCQ("霉变草样被拦", ONTOLOGY, "快检评级",
             {"batch_id": "b2",
              "measurements": {"CP": 20, "NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.2}},
             actor_role="养殖户", expect="reject", expect_rule="霉变拦截"),
    # guard：缺检测项应被「检测项完整」拦（缺 CP）
    ActionCQ("缺检测项被拦", ONTOLOGY, "快检评级",
             {"batch_id": "b3",
              "measurements": {"NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.0}},
             actor_role="养殖户", expect="reject", expect_rule="检测项完整"),
    # guard：越权角色应被「验质角色权限」拦（游客无权评级）
    ActionCQ("越权角色评级被拦", ONTOLOGY, "快检评级",
             {"batch_id": "b4",
              "measurements": {"CP": 20, "NDF": 40, "ADF": 30, "RFV": 140, "霉菌毒素": 0.0}},
             actor_role="游客", expect="reject", expect_rule="验质角色权限"),
)
