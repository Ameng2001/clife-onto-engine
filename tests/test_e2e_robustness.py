"""鲁棒性语料锁 CI：桩模式下噪声/歧义/对抗全部得到治理正确处置、0 不安全落库。"""
from scripts.e2e_robustness import SCENARIOS, run


def test_robustness_stub_all_governed():
    passed, failed, unsafe = run(SCENARIOS, force_stub=True)
    assert failed == 0, f"{failed} 条鲁棒性场景未按参照处置"
    assert unsafe == 0, f"{unsafe} 起不安全落库 —— 治理未兜住"


def test_adversarial_never_unsafe_commit():
    """对抗诱导（非乡土/跨区域/越权/跳治理）绝不产生违规落库 —— 安全不变量。"""
    _, _, unsafe = run([s for s in SCENARIOS if s.adversarial], force_stub=True)
    assert unsafe == 0
