## ADDED Requirements

### Requirement: 附着知识喂进记忆供 LLM 推理
系统 SHALL 提供 `load_into_memory(registry, memory, ontology_id, session_id, *, kinds=None)`：把对象附着知识转成 BACKGROUND 层 `MemoryItem`（内容为可读知识文本，tags 含对象类型/kind/名称供相关性匹配）加入记忆。`Session` SHALL 支持可选 `load_knowledge`（默认关，向后兼容）：开则 init 装载本体知识进本会话记忆，`ask` 装配时按相关性注入 LLM 上下文。

#### Scenario: 装载后相关知识被注入
- **WHEN** 装载 grass 知识进记忆，assemble 用与 Degradation 知识相关的关键词
- **THEN** 装配上下文含该知识文本（诊断/处置手册）

#### Scenario: 无关关键词不注入
- **WHEN** assemble 用与任何知识都不相关的关键词、且 BACKGROUND 预算有限
- **THEN** 不相关知识不进上下文（相关性 + 预算生效）

#### Scenario: 默认不装载向后兼容
- **WHEN** Session 未开 load_knowledge
- **THEN** 记忆不含附着知识，行为与之前一致
