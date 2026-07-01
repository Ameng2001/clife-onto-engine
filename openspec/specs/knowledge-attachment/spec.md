# knowledge-attachment Specification

## Purpose
TBD - created by archiving change add-knowledge-attachment. Update Purpose after archive.
## Requirements
### Requirement: 给对象声明标准化附着知识
系统 SHALL 支持给对象类型声明 `KnowledgeItem`（标准化 kind ∈ template|diagnostic|playbook|reference，含 content 与 refs），声明式、可 YAML 加载，与遥测绑定同层（槽位2）。内核 KnowledgeItem 行业无关，具体知识由插件提供。

#### Scenario: 声明与加载
- **WHEN** 插件为 Degradation 声明一条 diagnostic 知识
- **THEN** MappingRegistry.get_knowledge("grass","Degradation") 返回含该条的列表

### Requirement: 一次检索"对象+知识"（统一图，不跨层）
系统 SHALL 提供 `knowledge_for(registry, ontology, object_type) → tuple[KnowledgeItem]`——按对象类型取其全部附着知识；无绑定返回空。

#### Scenario: 取到对象的知识
- **WHEN** knowledge_for(reg,"grass","Degradation")
- **THEN** 返回该对象类型的知识项（名/类型/内容）

#### Scenario: 无绑定对象为空
- **WHEN** 对无附着知识的对象类型检索
- **THEN** 返回空，行为不受影响

### Requirement: Explorer 统一呈现对象+知识
自有 Explorer 点对象节点时 SHALL 除属性/遥测外，也列出该对象的附着知识（Palantir 式一屏见对象+知识）。

#### Scenario: 节点呈现附着知识
- **WHEN** render 一个有附着知识的对象（如 Degradation）
- **THEN** HTML 内嵌该对象的知识项，检视面板可列出

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

