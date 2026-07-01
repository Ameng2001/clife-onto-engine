## 1. 意图编译器 advise

- [x] 1.1 `CompiledIntent` 增 `answer` 字段 + kind 含 advise；`_SYSTEM` prompt 加 advise（判断类、答案基于知识、只读不编造）
- [x] 1.2 `compile`：认 kind=advise → CompiledIntent("advise", answer=…, confidence)

## 2. Session 路由 + 序列化

- [x] 2.1 `session.py`：`Reply` 增 answer；`ask` 路由 advise → Reply("advise", answer)（不碰引擎），回写 CONTEXT
- [x] 2.2 `web.py` reply_to_json：advise → {answer}

## 3. 测试 + smoke

- [x] 3.1 `tests/test_advise.py`：stub advise → Session 只读建议、不写库、进记忆；reply 序列化；做/查不受影响
- [x] 3.2 `scripts/smoke_advise.py`：stub advise 端到端（只读、进记忆、审计无写）

## 4. 收尾

- [x] 4.1 `check_kernel_purity.py` 通过；全量 pytest + smoke 全绿
- [x] 4.2 README §16 路线图加「咨询路径 advise（知识接地只读建议，闭合知识消费）」
- [x] 4.3 `openspec validate add-advise-path --strict`
