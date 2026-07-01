## 1. 知识绑定（槽位2，镜像遥测）

- [x] 1.1 `sdk/mapping.py`：`KnowledgeItem`（name/object_type/namespace/kind/content/refs）；`MappingRegistry.knowledge` + add/get_knowledge；`load_yaml` 支持 `knowledge:` 段
- [x] 1.2 `clife_onto_engine/knowledge.py`：`knowledge_for(registry, ontology, object_type)`

## 2. grass demo + Explorer 呈现

- [x] 2.1 grass `mappings/objects.yaml`：Degradation→诊断、Site→模板、RestorationMethod→参考
- [x] 2.2 `explorer.py` render：节点附 knowledge 元数据；检视面板列附着知识

## 3. 测试 + smoke

- [x] 3.1 `tests/test_knowledge.py`：声明/加载/检索；无绑定空；Explorer 节点含知识
- [x] 3.2 `scripts/smoke_knowledge.py`：grass 知识检索（对象+知识一次取）+ 类型覆盖

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图加「附着知识（多场景知识：吸收 Palantir 统一图 + UModel 模板化）」
- [x] 4.3 `openspec validate add-knowledge-attachment --strict`
