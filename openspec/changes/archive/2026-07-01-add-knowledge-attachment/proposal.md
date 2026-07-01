## Why

知识层多场景支持：吸收 Palantir 与 UModel 各自合理的做法，让同一套引擎能承载**多种性质的知识**，而不只是我们已有的强制型（Rule）与派生型（Function）。

- 吸收 **Palantir**：知识**挂到业务对象**、和对象**一次取到**（同一张图、同一套 Link/查询，不跨层多跳）。
- 吸收 **UModel**：**标准化的知识类型**（分析模板 / 诊断经验 / 处置手册 runbook / 领域参考），声明式、供 Agent 读着推理。

做法与遥测绑定同款（槽位2 声明式绑定）：**不新增元模型要素、不破五要素**。给对象声明**附着知识**，一次取"对象 + 它的知识"，Explorer 点对象即见。这样一套引擎里同时支持：强制知识（Rule）、派生知识（Function）、**参考/诊断知识（KnowledgeItem）**。

## What Changes

- `clife_onto_engine/sdk/mapping.py` 增 `KnowledgeItem`（name/object_type/namespace/kind/content/refs；kind ∈ template|diagnostic|playbook|reference）；`MappingRegistry` 增 `knowledge` 表 + add/get_knowledge；`load_yaml` 支持 `knowledge:` 段。
- `clife_onto_engine/knowledge.py`：`knowledge_for(registry, ontology, object_type) → tuple[KnowledgeItem]`（Palantir 式"对象+知识"一次取）。
- grass 声明附着知识：Degradation→诊断经验、Site→分析模板、RestorationMethod→领域参考。
- `explorer.py`：点对象节点除属性/遥测外，也列**附着知识**（Palantir 式统一视图，一屏见对象+知识）。
- 测试 + smoke：声明/加载/检索；Explorer 呈现；无绑定对象为空。
- **非破坏**：纯新增（槽位2 加一类绑定）；不改五要素/Rule/Function；行业无关（内核纯净 CI）。

## Capabilities

### New Capabilities
- `knowledge-attachment`: 给业务对象声明附着知识（标准化类型：分析模板/诊断/处置手册/领域参考），一次检索"对象+知识"（Palantir 统一图）、按标准类型声明（UModel 模板化），供读侧推理；与强制知识（Rule）、派生知识（Function）并存，支持多场景知识。

## Impact

- **改动代码**：`sdk/mapping.py`（+KnowledgeItem/绑定）、`knowledge.py`（新，检索）、`explorer.py`（节点呈现知识）、`plugins/grass/mappings/objects.yaml`（demo 知识）、`scripts/smoke_knowledge.py`、`tests/test_knowledge.py`。
- **红线守护**：只读检索；行业无关（内核 KnowledgeItem 无行业词，具体知识在插件）；与遥测绑定同层同模式。
- **多场景覆盖**：强制（Rule）+ 派生（Function）+ 附着参考/诊断（KnowledgeItem）三类知识共存于一套引擎。
