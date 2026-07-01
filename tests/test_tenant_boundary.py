"""租户→本体访问策略：授予/判定/default/YAML。"""
from __future__ import annotations

from clife_onto_engine.authz import TenantAccessPolicy


def test_grant_and_deny():
    p = TenantAccessPolicy(default_allow=False).grant("A", "grass")
    assert p.allows("A", "grass")
    assert not p.allows("A", "chili")       # 跨本体
    assert not p.allows("B", "grass")       # 跨租户
    assert not p.allows("X", "grass")       # 未知租户 default-deny


def test_default_allow():
    p = TenantAccessPolicy(default_allow=True)
    assert p.allows("anyone", "grass")


def test_allowed_ontologies():
    p = TenantAccessPolicy().grant("A", "grass", "chili")
    assert p.allowed_ontologies("A") == frozenset({"grass", "chili"})


def test_yaml_load(tmp_path):
    y = tmp_path / "t.yaml"
    y.write_text("default_allow: false\ntenants:\n  - tenant: A\n    ontologies: [grass]\n",
                 encoding="utf-8")
    p = TenantAccessPolicy().load_yaml(str(y))
    assert p.allows("A", "grass") and not p.allows("A", "chili")
