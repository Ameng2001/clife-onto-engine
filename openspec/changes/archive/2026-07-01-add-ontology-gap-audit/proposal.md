## Why

C1 的运行时形式：**本体治理缺口审计**。studio-ontology 从业务分析编译出插件骨架时，function-backed 规则/Action 回写留 `TODO(FDE)`——运行时需要一把静态审计尺子，扫 registry 回答**"这个本体还有哪些没填完/治理缺口"**：哪个 Action 没 handler、哪条规则引用悬空、哪条规则没出处、哪个关系端点不存在。

这是 FDE 建模→运行时闭环里"缺口可见"的一环，也补齐 OKF（无引用规则标"待补"）——把治理缺口从"跑到才炸"提前到"上线前静态可查"。

## What Changes

- 新增 `clife_onto_engine/gaps.py`：`audit_gaps(registry, ontology_id) → GapReport`。分两级：
  - **blocking**（结构性，会在运行时炸）：Action 无 handler（impl=None）、guard/post_rule 引用未注册规则、writes 指向未声明对象、Function 无 impl、Link 端点对象不存在。
  - **advisory**（治理完整性）：Rule 无 `source`（出处缺口，补 OKF citations 审计）。
- `GapReport`：blocking/advisory 明细（kind/subject/detail）+ 计数 + `ok`（无 blocking）+ summary。
- 测试 + smoke：grass **无 blocking**（结构完整），列出 advisory（declarative guard 无出处）；构造残缺版本（去 handler / 悬空引用）→ blocking 精确定位。
- **非破坏**：纯新增、只读静态扫描；行业无关（内核纯净 CI）。

## Capabilities

### New Capabilities
- `ontology-gap-audit`: 对某本体静态审计治理/完整性缺口，分 blocking（结构性、会运行时失败）与 advisory（治理文档缺口），精确定位到具体 Action/Rule/Link。上线前可查、补 studio-ontology 骨架的 TODO(FDE) 缺口与 OKF 出处缺口。

## Impact

- **新增代码**：`clife_onto_engine/gaps.py`、`scripts/smoke_gaps.py`、`tests/test_gaps.py`。
- **红线守护**：只读静态扫描（不执行、不落库）；行业无关（内核纯净 CI）。
- **承接**：C1 的运行时可查缺口；与 CQ 验收（C3，跑得对不对）、变更影响（B2）互补——CQ 验行为、gap 审计验完整性。C1 的 codegen 回填（真正"填"stub）仍在建模端。
