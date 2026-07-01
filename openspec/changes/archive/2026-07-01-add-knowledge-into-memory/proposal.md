## Why

附着知识已能声明/检索/在 Explorer 呈现，但还没被 **Agent/LLM** 消费。把它喂进四层记忆的 **BACKGROUND 层**，`Session.ask` 装配记忆时按相关性把**相关知识**注入意图编译器上下文——LLM 就能**基于领域知识推理**（诊断经验/处置手册/分析模板/参考），而不只是查数据。这才闭合"知识供 Agent 读着推理"的消费侧。

## What Changes

- `clife_onto_engine/knowledge.py` 增 `load_into_memory(registry, memory, ontology_id, session_id, *, kinds=None) → int`：把附着知识项转成 `MemoryItem`（layer=BACKGROUND、content=可读知识文本、tags=(对象类型,kind,名称) 供相关性匹配、source="knowledge"、bound_entity=对象类型）加入记忆。
- `Session` 增可选 `load_knowledge=False`：为 True 时 init 把本体附着知识装进本会话记忆（一次），后续 `ask` 装配即按相关性注入。
- 测试 + smoke：装载后 assemble（相关关键词）注入对应知识文本；无关关键词不注入（相关性生效）；预算内择优。
- **非破坏**：默认 load_knowledge=False（既有行为不变）；纯新增；行业无关（内核纯净 CI）。

## Capabilities

### Modified Capabilities
- `knowledge-attachment`: 附着知识**可喂进四层记忆 BACKGROUND 层**，经 `Session.ask` 的记忆装配按相关性注入 LLM 上下文——知识从"可检索"走到"被 Agent 读着推理"。

## Impact

- **改动代码**：`knowledge.py`（+load_into_memory）、`session.py`（+load_knowledge 开关）、`scripts/smoke_knowledge_memory.py`、`tests/test_knowledge_memory.py`。
- **红线守护**：只读装载（把声明知识转记忆，不改知识/五要素）；相关性 + token 预算复用既有 assemble；行业无关；默认关即兼容。
- **闭合知识消费**：声明（槽位2）→ 检索（knowledge_for）→ 呈现（Explorer）→ **推理（Memory→LLM）**。
