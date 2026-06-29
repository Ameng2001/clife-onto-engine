"""pytest 共享夹具。导入草业/辣椒插件完成 SPI 注册（全局 registry）。

CI 只跑离线、确定性测试；接 LLM（意图编译器）与真 NebulaGraph 的路径不在此覆盖。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pytest

import plugins.grass  # noqa: F401,E402 — 注册 grass
import plugins.chili  # noqa: F401,E402 — 注册 chili

from clife_onto_engine.query import InMemoryStore, StagedLink  # noqa: E402
from clife_onto_engine.sdk import Actor  # noqa: E402


@pytest.fixture
def grass_store() -> InMemoryStore:
    """草业参考数据（动作用）+ 查询子图（OQL 用）。"""
    from plugins.grass import seed_reference_data
    s = InMemoryStore()
    seed_reference_data(s)  # Site parcel_001 + 乡土名录
    s.put_object("Site", "parcel_002", {"parcel_id": "parcel_002", "region": "锡林郭勒", "site_type": "草原"})
    s.put_object("Degradation", "deg1", {"deg_id": "deg1", "level": "重度", "type": "盐渍化"})
    s.put_object("RestorationMethod", "m1", {"method_id": "m1", "name": "喷播"})
    s.put_object("RestorationMethod", "m2", {"method_id": "m2", "name": "补播"})
    s.put_link(StagedLink("suffers", "Site", "parcel_001", "Degradation", "deg1"))
    s.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m1"))
    s.put_link(StagedLink("treated_by", "Degradation", "deg1", "RestorationMethod", "m2"))
    return s


@pytest.fixture
def contractor() -> Actor:
    return Actor("u1", "施工方")
