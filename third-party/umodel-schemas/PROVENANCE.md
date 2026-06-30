# Vendored: UModel schema 规格（只读）

- **来源**：https://github.com/alibaba/UnifiedModel — `schemas/` 目录
- **钉定 commit**：`fa130fbe756cea8f093e4832bf917fba3ea4dc0c`
- **License**：Apache-2.0（与本仓库同；另已就深度使用达成协议）
- **用途**：**仅供离线校验**本仓库导出的 UModel model pack（`scripts/smoke_umodel.py`）。
  不参与运行时、不被 import 进引擎、不随产物分发执行逻辑。
- **范围**：只 vendor 声明式 schema 规格（YAML）。**不** vendor UModel 的 Go server/query/web 源码——
  那是运行时服务,以容器 sidecar 形态引入（见 `docs/04-umodel-interop.md`），不进本源码树。

## 升级约定

UModel schema 随上游版本演进。本目录对**单一钉定 commit** 负责;
升级 = 重新 `cp` + 改本文件 commit/version + 跑 `scripts/smoke_umodel.py` 回归,是显式 PR 动作。

## 目录

```
schemas/
  base.yaml                    # schema 元定义（语法、约束表达式语言）
  manifest.yaml                # kind → schema 清单
  core/{dataset,link,storage}/ # 各 kind 的 schema（entity_set / entity_set_link / data_link / storage_link / ...）
  includes/                    # 复用类型（metadata / field_spec / link / ...）
```
