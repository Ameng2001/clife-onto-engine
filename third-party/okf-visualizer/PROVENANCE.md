# third-party / okf-visualizer

Vendored 子集：OKF（Open Knowledge Format）官方**参考可视化器**——把一个 OKF Bundle
渲染成单文件、自包含、交互式的知识图谱 HTML（无后端、数据不出本地）。

## 来源

- 上游：https://github.com/GoogleCloudPlatform/knowledge-catalog —— `okf/src/reference_agent/`
- 分支：`main`（2026-06 OKF v0.1 发布版）
- 许可证：**Apache License 2.0**（见 `LICENSE.md`，随上游一并 vendored）
- 版权：Google LLC

## 包含的文件（最小子集）

```
reference_agent/
  __init__.py                 ← 本仓库置空（见下"改动"）
  bundle/
    __init__.py               ← 本仓库置空（见下"改动"）
    document.py               ← 上游原文（OKF frontmatter+正文解析，仅依赖 pyyaml）
  viewer/
    __init__.py               ← 上游原文（导出 generate_visualization）
    generator.py              ← 上游原文（walk bundle → 图 → 填模板）
    templates/viz.html        ← 上游原文
    static/viz.css            ← 上游原文
    static/viz.js             ← 上游原文
```

## 对上游的改动（最小化）

- `reference_agent/__init__.py` 与 `reference_agent/bundle/__init__.py` **置为空文件**：
  上游这两个包 `__init__` 会拖入完整 reference agent 的依赖（BigQuery / google-genai 等），
  而我们只用"可视化器 + OKF 解析器"。置空后导入链仅为
  `reference_agent → bundle.document(pyyaml) / viewer.generator`，零额外依赖。
- 未改动任何被使用文件的源码逻辑。

## 我们在导出端做的增强（均不改 vendored 文件）

`scripts/export_okf.py` 在调用可视化器前后做三件事，vendored 源码一字未改：
1. **类型配色**：运行时给 `generator._TYPE_PALETTE` 赋值，把本体五类（对象/规则/动作/函数/关系）
   上不同颜色（`to_node` 调用时读该模块全局，故无需改文件）。
2. **离线内联**：生成后把 CDN `<script src>` 替换为 vendored 库内联（见上）。
3. **类型图例**：向 HTML 注入左下角固定图例（颜色取自同一份 palette，单一来源不漂移）。

## 唯一运行依赖

`PyYAML`（已在本仓库 `requirements.txt`）。

## 用法（已接入导出流程）

```python
import sys, pathlib
sys.path.insert(0, "third-party/okf-visualizer")
from reference_agent.viewer import generate_visualization
generate_visualization(bundle_dir, bundle_dir / "viz.html", bundle_name="grass")
```

`scripts/export_okf.py` 在导出每个 OKF 包后自动调用它，产出 `build/okf/<ns>/viz.html`。

## 注意

- 该参考实现只把**相对** md 链接画成边，**跳过** bundle-relative 绝对链接(`/...`)；
  故 `clife_onto_engine/okf.py` 导出时对跨概念链接用相对路径（`../rules/x.md`），两种皆 OKF 合法。
- 这是 vendored 第三方源码（非 pip 依赖），按本仓库约定放 `third-party/`。
- **离线性（已做成完全离线）**：`cytoscape@3.28.1` 与 `marked@12.0.0` 两个 JS 库已 vendor 到
  `reference_agent/viewer/static/vendor/`（各自 Apache-2.0 / MIT，带版权头）。`scripts/export_okf.py`
  在生成 `viz.html` 后会把这两个库**内联**进 HTML（替换原 CDN `<script src>`），产出
  **单文件、零外链、数据与库都不出本地**的自包含 HTML（~426KB）——满足内网/离线审计（政务/备案）。
  内联在我们的导出脚本里做，**未改动 vendored 上游模板/生成器**。
