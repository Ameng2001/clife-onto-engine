"""LLM 客户端 —— provider 无关的协议 + OpenAI 兼容薄 adapter（跑在官方 openai SDK 上）。

内核只依赖 `LLMClient` 协议；具体接哪家（Qwen/DashScope、OpenAI、本地兼容端点…）是 adapter。
不造大轮子：复用 openai SDK 的兼容模式。密钥从 env / 本地文件读取，绝不写进源码。
"""
from __future__ import annotations

import json
import os
import pathlib
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def complete_json(self, system: str, user: str) -> dict:
        """让模型只输出一个 JSON 对象并解析返回（system 里已含字段约定）。"""
        ...


def _load_config(config_path: Optional[str]) -> dict:
    """优先 env，其次本地文件。env 名兼容 DASHSCOPE_* 与 OPENAI_*。"""
    base = (os.getenv("DASHSCOPE_BASE_URL") or os.getenv("OPENAI_BASE_URL"))
    key = (os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY"))
    model = os.getenv("LLM_MODEL")
    cfg = {}
    if config_path and pathlib.Path(config_path).exists():
        cfg = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
    return {
        "base_url": base or cfg.get("base_url"),
        "api_key": key or cfg.get("api_key"),
        "model": model or cfg.get("model"),
    }


class ReplayLLMClient:
    """回放录制的 LLM 原始输出（record-replay / VCR 式）——确定性、无网络。

    把真 Qwen 的编译行为**固化为 CI 回归**：`scripts/record_qwen.py` 用真 Qwen 录一次
    每句口语的原始 JSON 到 fixture；CI 用本客户端按口语键重放同一 JSON，编译器逐字跑
    真实解析/校验逻辑。按**口语**键（从 user 的「用户说：」后提取），对 manifest 变化鲁棒。
    """

    def __init__(self, recordings: dict) -> None:
        self._rec = dict(recordings)      # {utterance: 原始 JSON dict}

    @staticmethod
    def utterance_of(user: str) -> str:
        return user.split("用户说：")[-1].strip()

    def complete_json(self, system: str, user: str) -> dict:
        utt = self.utterance_of(user)
        if utt not in self._rec:
            raise KeyError(f"无录制: {utt!r}（先跑 scripts/record_qwen.py 录制真 Qwen 输出）")
        return self._rec[utt]


class OpenAICompatibleClient:
    """适配任何 OpenAI 兼容端点（含阿里 DashScope/Qwen）。"""

    def __init__(self, *, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, config_path: Optional[str] = "llm.local.json",
                 temperature: float = 0.0) -> None:
        cfg = _load_config(config_path)
        self.base_url = base_url or cfg["base_url"]
        self.model = model or cfg["model"]
        self.temperature = temperature
        key = api_key or cfg["api_key"]
        if not (self.base_url and key and self.model):
            raise RuntimeError("LLM 配置缺失：需 base_url / api_key / model（env 或 llm.local.json）")
        from openai import OpenAI
        self._client = OpenAI(base_url=self.base_url, api_key=key)

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=self.temperature,
            extra_body={"enable_thinking": False},  # 关闭思考模式，拿干净 JSON
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
