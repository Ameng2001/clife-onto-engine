## ADDED Requirements

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
