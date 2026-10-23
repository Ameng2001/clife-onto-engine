"""IntentCompiler 动作名归一化：LLM 写 "上架产品 SKU" / "上架产品ＳＫＵ" 也能命中注册名 "上架产品SKU"。

只做字形与空白归一（NFKC + 去空白），不做模糊匹配；歧义时仍判清单外。
"""
from __future__ import annotations

from clife_onto_engine.intent.compiler import IntentCompiler, normalize_name
from clife_onto_engine.intent.llm import ReplayLLMClient
from clife_onto_engine.metamodel import ActionDef, ParamSpec
from clife_onto_engine.sdk.registry import Registry


def _registry(*names: str, ns: str = "t") -> Registry:
    """Registry 的动作表只在 spi.action 装饰器里写；测试直接填 actions 字典（同一把键）。"""
    reg = Registry()
    for n in names:
        reg.actions[(ns, n)] = ActionDef(name=n, namespace=ns, description="",
                                         params=(ParamSpec("x", "string", required=True),))
    return reg


def _compile(reg, action_name: str):
    raw = {"kind": "action", "action": action_name, "params": {"x": "1"}, "confidence": 0.9}
    comp = IntentCompiler(ReplayLLMClient({"u": raw}), reg)
    return comp.compile("t", "u")


def test_normalize_name_nfkc_and_whitespace():
    assert normalize_name("上架产品 SKU") == "上架产品SKU"
    assert normalize_name("上架产品ＳＫＵ") == "上架产品SKU"
    assert normalize_name(" 创建服务包　SKU ") == "创建服务包SKU"
    assert normalize_name("") == ""


def test_exact_name_still_wins_and_is_returned_canonical():
    reg = _registry("上架产品SKU")
    for spelled in ("上架产品SKU", "上架产品 SKU", "上架产品ＳＫＵ", "上架 产品 SKU"):
        it = _compile(reg, spelled)
        assert it.kind == "action", (spelled, it.error)
        assert it.action == "上架产品SKU"  # 返回规范名，下游 get_action 精确可查


def test_unknown_and_ambiguous_still_rejected():
    reg = _registry("上架产品SKU")
    assert _compile(reg, "上架产品").kind == "reject"
    assert _compile(reg, "下架产品SKU").kind == "reject"
    # 两个注册名归一化后撞键（极端情况）：歧义不猜，仍清单外
    amb = _registry("上架产品SKU", "上架产品 SKU")
    assert _compile(amb, "上架产品ＳＫＵ").kind == "reject"


def test_other_ontology_not_matched():
    reg = _registry("上架产品SKU")
    reg.actions[("other", "其它")] = ActionDef(name="其它", namespace="other")
    raw = {"kind": "action", "action": "其它", "params": {}, "confidence": 0.9}
    it = IntentCompiler(ReplayLLMClient({"u": raw}), reg).compile("t", "u")
    assert it.kind == "reject"
