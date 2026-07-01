"""租户数据接入：mengcao 样例声明式落库 + schema 校验拒脏行 + 真数据上 CQ 通过。"""
import pathlib

from clife_onto_engine.cq import run_cq_suite
from clife_onto_engine.query import InMemoryStore
from clife_onto_engine.sdk import spi
from clife_onto_engine.tenant import load_tenant

import plugins.grass  # noqa: F401
from plugins.grass.cq import CQ_SUITE

ROOT = pathlib.Path(__file__).resolve().parent.parent
MENGCAO = ROOT / "tenants" / "mengcao" / "tenant.yaml"


def test_mengcao_sample_loads_by_schema():
    store = InMemoryStore()
    rep = load_tenant(MENGCAO, spi.registry, store)
    assert rep.total_rejected == 0
    by = {o.object_type: o for o in rep.objects}
    assert by["Site"].loaded == 4
    assert by["NativeListing"].loaded == 4
    assert by["ForageSample"].loaded == 3
    # 组合主键模板生效：region::species 键可取到
    assert store.get_object("NativeListing", "巴彦淖尔::碱茅") is not None
    # 数字类型强制：area_mu 落成 number 而非字符串
    assert store.get_object("Site", "parcel_001")["area_mu"] == 500
    # 完备度反映缺列（parcel_103 缺 site_type）
    assert by["Site"].completeness < 1.0


def test_cq_passes_on_loaded_tenant_data():
    store = InMemoryStore()
    load_tenant(MENGCAO, spi.registry, store)
    cq = run_cq_suite(CQ_SUITE, spi.registry, store=store)
    assert cq.failed == 0, [r.name for r in cq.results if not r.passed]


def test_schema_validation_rejects_dirty_rows(tmp_path):
    # 造脏数据：缺主键、必填缺失、数字非法 —— 应逐行拒绝并留原因，不静默丢、不崩
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "sites.csv").write_text(
        "parcel_id,area_mu,region,site_type\n"
        "good_1,500,巴彦淖尔,盐碱\n"          # ok
        ",320,巴彦淖尔,盐碱\n"                # 缺主键
        "bad_2,,巴彦淖尔,盐碱\n"              # 缺必填 area_mu
        "bad_3,不是数字,巴彦淖尔,盐碱\n"       # area_mu 非数字
        "bad_4,410,,盐碱\n",                 # 缺必填 region
        encoding="utf-8")
    (tmp_path / "tenant.yaml").write_text(
        "tenant: t\nontology: grass\nsources:\n"
        "  - object: Site\n    file: data/sites.csv\n    format: csv\n",
        encoding="utf-8")
    store = InMemoryStore()
    rep = load_tenant(tmp_path / "tenant.yaml", spi.registry, store)
    site = next(o for o in rep.objects if o.object_type == "Site")
    assert site.loaded == 1                       # 只有 good_1 落库
    assert len(site.rejected) == 4                # 四条脏行全部留痕
    reasons = " ".join(r for _, r in site.rejected)
    assert "主键" in reasons and "area_mu" in reasons and "region" in reasons


def test_unknown_object_rejected(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.csv").write_text("k\nv\n", encoding="utf-8")
    (tmp_path / "tenant.yaml").write_text(
        "tenant: t\nontology: grass\nsources:\n"
        "  - object: NotAThing\n    file: data/x.csv\n    format: csv\n",
        encoding="utf-8")
    rep = load_tenant(tmp_path / "tenant.yaml", spi.registry, InMemoryStore())
    assert rep.total_loaded == 0 and rep.total_rejected == 1
