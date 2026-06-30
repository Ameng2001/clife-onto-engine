# 04 · UModel 互操作定位（读层 vs 写层）

> 纠偏卡。与 [`02-oag-positioning.md`](02-oag-positioning.md)（OAG vs RAG/Skill）、
> [`03-okf-positioning.md`](03-okf-positioning.md)（OKF 文档层 vs 执行层）同系列：
> 划清 **UModel = 只读语义层** 与 **clife-onto-engine = 受治理写层** 的层次纪律。

---

## 1. 一句话

UModel（Alibaba UnifiedModel）与本引擎是"企业语义 OS"的**两个互补半区,几乎不重叠**:

| | clife-onto-engine（本仓库） | UModel |
|---|---|---|
| 本质 | 受治理的**做**(OAG / 写路径) | 受治理的**读 / 上下文供给**(语义读层) |
| 核心 | Action 引擎:guard→写后规则→**确定性回滚**→审计;HIL;置信度 | YAML model pack · SPL(`.umodel/.entity/.topo`) · MCP 读工具 · Web Explorer · 遥测 query-plan · 多语言 SDK |
| 对世界 | **写**(受规则约束) | **只读** |
| 出错后果 | 状态被错误改变(故需引擎兜底) | 答案/视图不准 |

> 结论:UModel 强在我们**刻意做薄**的读/发现/可视化/agent 接入半区;我们强在它**压根没有**的治理写半区。
> 所以"利用"= 把 UModel 当作本引擎**底座之上的官方只读层**,而非替换内核任何一块。
> 这与 [README 分层](../README.md#layering)"本体是底座、skill/agent 是调用方"一致——查路径是
> **OAG 基底上的结构化受控读,非 RAG**。

---

## 2. 分层视图

```
   交互层（台面）：Web Explorer / SPL / MCP agent ── 由 UModel 承担（读）
        │  只读:SPL / MCP query_spl_execute / REST query
        ▼
   ┌─────────────────────────────────────────────┐
   │ UModel 只读语义层（第三方服务,compose sidecar）│  ← 装载本引擎导出的 model pack
   └─────────────────────────────────────────────┘
        ▲  导出(export_pack)              ▲  受治理的写永远走这里 ↓
        │                                  │
   ┌─────────────────────────────────────────────┐
   │ clife-onto-engine（底座,写）：Action 引擎     │  ← 本仓库:guard→回滚→审计
   └─────────────────────────────────────────────┘
```

- **导出方向**:`clife_onto_engine/umodel.py` 把五要素 registry(读半区)编译成 UModel pack。
- **写方向**:UModel **不**提供受治理写;任何写仍只经引擎 Action 引擎。引擎**不依赖** UModel 即可运行,UModel 可随时关停。

---

## 3. 契约映射(五要素 → UModel kinds)

| 五要素 | UModel kind | 导出器处理 |
|---|---|---|
| `ObjectType`(+ 属性) | `entity_set`(`spec.fields`) | 主键补成存在的 field;`primary_key_fields`/`id_generator`/`name_fields`;状态机落只读 `tags` |
| `LinkType`(有向、边语义) | `entity_set_link` | `src`/`dest` 两端 entity_set;`entity_link_type`=Link 名;边语义落 `description`(仅展示) |
| 映射注册表 槽位2(对象→物理表/列) | `external_storage` | 每个物理落点一条(type=store,name=table),表/列/物化策略落 `tags`;object↔storage 的 `entity_source_link` 留后续 |
| 运行时对象实例 | `sample-data/entities.json` | `__entity_id__` 由对象主键确定性派生(可重放) |
| 运行时关系实例 | `sample-data/relations.json` | src/dest/relation;仅导引用闭合(两端类型均属本 ontology)的边 |
| `Function` / `Rule` / `Action` | **不映射** | 治理写留引擎;Rule 至多作只读元数据注解,标注 metadata 非 enforcement |

> 字段精确性以 vendored 的 `third-party/umodel-schemas/` 为准;`scripts/smoke_umodel.py` 离线校验导出 pack 合规。

---

## 4. 红线（违反即层次错乱）

1. **治理写不进 UModel** —— `Function`/`Rule`/`Action` 不导出为任何可执行 UModel 元素。受治理写永远经引擎 Action 引擎(guard→写后规则→回滚→审计);UModel 是只读层,提供"读对象图",不提供"受治理地写回"。
2. **不 vendor UModel 的 Go 源码进本仓库** —— server/query/web/MCP 是 Go 运行时,以**容器 sidecar**形态引入(镜像从上游构建),不进 Python 源码树、不进构建链。这是**工程负担**判断,与 license 无关(license 已深度授权)。只 vendor 其**只读 schema 规格**(`third-party/umodel-schemas/`)供离线校验。
3. **不用 SPL 替换 OQL** —— OQL(JSON AST、防注入)仍是引擎内的受治理读;UModel SPL 是外部浏览面。两者并存,职责不同。
4. **引擎不依赖读层** —— `serve.py` / `Session.ask` / `/ask` 的启动与运行不依赖 UModel server;读层挂了,引擎照常做/查。

---

## 5. 用法

```bash
# 1) 导出本体 → UModel pack（只读半区：对象/关系/物理映射/运行时实例）
python scripts/export_umodel.py            # → build/umodel/<ontology>/

# 2) 离线校验导出 pack 合 UModel schema（无网络、无 Go 进程，CI 同款）
python scripts/smoke_umodel.py

# 3) 起读层 sidecar 并装载 + 在线权威验收（一次性从上游构建镜像）
docker build -f deployments/docker/Dockerfile -t umodel-open-source:local .   # 在 UModel 仓库内
docker run -d --name umodel-verify -p 8081:8080 -v "$PWD/build/umodel:/packs:ro" \
  umodel-open-source:local --addr :8080 --data /data --graphstore file.memory --import-root /packs
bash scripts/verify_umodel_online.sh          # import/写实例/SPL 全经真实 UModel；浏览 http://localhost:8081
```

锁进 CI:`tests/test_umodel_export.py`(结构保真 / 治理写不外泄 / 确定性 / 离线校验)。

> **已用真实 UModel server 验证**(镜像从 alibaba/UnifiedModel 构建):grass 导出 pack 经公共 REST 装载——
> `import` 14/14 元素 0 skipped、`entities:write` 7/7、`relations:write` 3/3 全被真实 UModel 校验接受;
> `.umodel` 列出 7 个 entity_set、`.entity` 查到 `parcel_001/巴彦淖尔/盐碱`、`.topo` cypher 遍历到 suffers/treated_by 关系。
> 关键修正:`__entity_id__` 必须是 (domain,type,key) 的确定性 32-hex(md5),观测时间窗必填——已落 `clife_onto_engine/umodel.py`。

---

## 6. 治理写桥（phase 2，已实现）

让 MCP agent 在同一会话**既读对象图、又触发受治理的写**——两半区合体成完整 OAG。
**关键:不开 UModel 自己的 `entity_write` 写旁路**(那会绕过治理)。写**只**经引擎,UModel 只接收已提交结果。

```
   MCP agent
     │  query（读，默认开）          act（写，opt-in）
     ▼                                ▼
   引擎 OQL（受治理读）        引擎 ActionEngine：guard→写后规则→提交/确定性回滚→审计
                                      │  仅 decision==committed
                                      ▼
                          反映已提交对象 → UModel REST entities:write（读层同步）
                          rejected / pending_hil → 不反映（本体兜底 / 待人工复核）
```

- 实现:`clife_onto_engine/mcp/`(`GovernedBridge` 传输无关核心 + 最小 JSON-RPC stdio `server.py`),入口 `scripts/serve_mcp.py`。
- **连接**(Claude Code / Cursor 等把它当 stdio 子进程拉起):
  ```json
  // .mcp.json
  { "mcpServers": { "clife-onto-engine": {
      "command": "python", "args": ["scripts/serve_mcp.py"],
      "env": { "ONTO": "grass", "ONTO_ENABLE_ACT": "1", "UMODEL_URL": "http://localhost:8081" } } } }
  ```
  `ONTO_ENABLE_ACT=1` 才暴露 `act`(opt-in);`UMODEL_URL` 设了才提交后反映进读层(不设则只做不反映)。
- 红线(都有测试断言,`tests/test_mcp_bridge.py` / `scripts/smoke_mcp_bridge.py`):
  ① 写只经 `ActionEngine`,UModel `entity_write`/`entity_expire` 保持 disabled(无写旁路);
  ② 只反映 `committed`;`rejected`/`pending_hil` 零反映;
  ③ 反映失败不回滚引擎提交(读层最终一致、引擎不依赖读层)。
- **已用真实 UModel 验证**(`scripts/verify_mcp_bridge_online.sh`):
  `act 出一地一方(碱茅)` → 引擎提交、反映 2 对象 → `.entity` 查到 Project/SeedPack;
  `act 出一地一方(紫花苜蓿)` → 引擎 `乡土合规` 确定性拒绝 → 读层零脏写。**这是"LLM 提议、本体兜底"在 UModel 同台的活证据。**

## 7. 仍推迟

- **关系反映**:`act` 当前反映已提交对象;若 Action 经 `stage_link` 写关系,需 `ActionResult` 暴露 staged links 才反映(本期动作只写对象,记 TODO)。
- **object↔storage 的 `entity_source_link`**:UModel `entity_source` 当前 experimental、无样例,贸然导会校验失败;现以 `external_storage` 承载后端可见性,待上游稳定再补对象↔源的 link。
