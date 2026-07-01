## Why

真 Qwen 端到端验证暴露的缺口：LLM 明明能基于附着知识对"该怎么做/直接喷播行不行/先做什么"这类**判断类**问题给出**领域正确的建议**（贴处置手册：重度盐碱先改良再喷播），却被引擎硬塞进 "clarify" 的壳里吐出来——因为引擎没有"咨询/建议"路径，只有 做(action)/查(query)/澄清(clarify)。

补一个 **advise 咨询路径**：让"知识接地的领域建议"成为**一等回复类型**（只读、不写库、不越权）。知识消费从"进上下文→改推理"再走到"产出建议"，闭合价值。与 OAG 一致：建议是**低风险只读**（理解侧），真要做仍走**受治理动作**（执行侧）。

## What Changes

- `intent/compiler.py`：`CompiledIntent` 增 `answer` 字段与 `kind="advise"`；`_SYSTEM` prompt 教 LLM 何时用 advise（判断/建议类问题，答案**须基于提供的相关记忆/知识**，只读不写、不编造清单外事实）；`compile` 认 advise 并回 `answer`。
- `session.py`：`ask` 路由 `kind=="advise"` → `Reply("advise", answer=...)`（只读，不碰引擎/不写库），回写 CONTEXT 记忆。
- `web.py` reply_to_json 支持 advise（answer）。
- 测试 + smoke：stub 返回 advise → Session 回只读建议、不写库、进记忆；reply 序列化。
- **非破坏**：纯新增一类意图/回复；做/查/澄清/拒绝不变；无 answer 的旧行为不变；行业无关。

## Capabilities

### New Capabilities
- `advise-path`: 意图编译器可对判断/建议类问题产出 `advise`（知识接地的只读领域建议），Session 作为一等回复返回（不写库、不越权、进记忆）。补齐知识消费的"产出建议"一环；与受治理动作分层（建议只读、动作受治理）。

## Impact

- **改动代码**：`intent/compiler.py`（advise kind + answer + prompt）、`session.py`（advise 路由 + Reply.answer）、`web.py`（序列化）、`scripts/smoke_advise.py`、`tests/test_advise.py`。
- **红线守护**：advise **只读**（不进 Action 引擎、不写库、不越权）；建议须基于知识（prompt 约束，防幻觉在执行层不变——真动作仍受治理兜底）；行业无关（内核纯净 CI）。
- **闭合知识消费**：声明→检索→呈现→推理→**产出建议**。
