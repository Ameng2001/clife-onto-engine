## 1. 知识→记忆

- [x] 1.1 `knowledge.py`：`load_into_memory(registry, memory, ontology, session_id, *, kinds=None)`——KnowledgeItem→MemoryItem(BACKGROUND, content, tags=(对象,kind,名), source=knowledge, bound_entity=对象)
- [x] 1.2 `session.py`：`Session(..., load_knowledge=False)`；True 时 init 装载本体知识进本会话记忆

## 2. 测试 + smoke

- [x] 2.1 `tests/test_knowledge_memory.py`：装载后 assemble 相关关键词注入知识；无关不注入；默认关兼容；kinds 过滤
- [x] 2.2 `scripts/smoke_knowledge_memory.py`：grass 知识入记忆→相关 utterance 装配含知识文本

## 3. 收尾

- [x] 3.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 3.2 README §16 路线图更新「附着知识」条：喂进 Memory 供 LLM 推理
- [x] 3.3 `openspec validate add-knowledge-into-memory --strict`
