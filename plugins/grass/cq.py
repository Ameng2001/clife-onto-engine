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
    # 会查：某盟市应查得到地块
    QueryCQ("某区域有地块", ONTOLOGY,
            OQLQuery(namespace=ONTOLOGY, start="Site",
                     where=(Cond("region", "eq", "巴彦淖尔"),)),
            min_rows=1),
)
