## 1. Vendor UModel schema(只读规格,离线校验地基)

- [x] 1.1 把 UModel `schemas/*.yaml`(base/core/includes/manifest)拷入 `third-party/umodel-schemas/`,钉定上游 commit/version
- [x] 1.2 加 `third-party/umodel-schemas/PROVENANCE`(来源、版本、用途:仅离线校验)
- [x] 1.3 写最小 schema 加载器:解析 vendored schema,暴露各 kind 的必填字段/类型(供 smoke 用)

## 2. 导出器 `clife_onto_engine/umodel.py`(行业无关,与 okf.py 同层)

- [x] 2.1 搭骨架:`export_pack(registry, ontology_id) -> dict/目录`,复用 `okf.export_bundle` 的遍历范式
- [x] 2.2 `ObjectType → entity_set`:fields / primary_key_fields / id_generator / name_fields
- [x] 2.3 `LinkType → entity_set_link`:src/dest 解析两端 entity_set,关系类型 = Link 名,边属性映射
- [x] 2.4 映射注册表 → `data_link` + `storage_link` + storage 定义(虚拟/物化/混合 → storage kind)
- [x] 2.5 运行时实例 → `entities.json` / `relations.json`,`__entity_id__` 由对象主键确定性派生(可重放)
- [x] 2.6 显式排除 Function/Rule/Action 的可执行映射;Rule 仅作只读元数据注解(标注 metadata 非 enforcement)
- [x] 2.7 产出 UModel 目录布局:`umodel/<domain>/{entity_set,link,storage}/*.yaml` + `sample-data/*.json`,domain=workspace=ontology_id

## 3. 脚本与离线 smoke

- [x] 3.1 `scripts/export_umodel.py`:grass registry → pack 落盘到约定目录
- [x] 3.2 `scripts/smoke_umodel.py`:对导出 pack 跑 vendored-schema 离线结构校验(无网络、无 Go 进程),退出码语义化
- [x] 3.3 反例用例:删一个必填 `metadata.name`,断言离线校验拦截并定位违规元素

## 4. 读层 sidecar(compose 默认起)

- [x] 4.1 `docker-compose.yml` 加 `umodel-server` 服务(默认起,`--graphstore file.memory`,挂载 grass 导出目录)
- [x] 4.2 启动编排:服务起后 `import` 装载 pack(或挂载即载),Explorer 端口对外
- [x] 4.3 验证引擎解耦:停掉 `umodel-server`,`serve.py` / `/ask` 做/查/澄清照常,既有 28 项测试不受影响

## 5. 在线权威校验(可选,sidecar 在时)

- [x] 5.1 sidecar 起着时跑 `umctl umodel validate`(或 REST `/validate`)做权威校验,与离线 smoke 结果对账
- [x] 5.2 人工 Explorer 验收:grass 对象图可浏览、`.umodel`/`.entity`/`.topo` 能查到对象/关系

## 6. 文档与红线固化

- [x] 6.1 写 `docs/04-umodel-interop.md`:读层 vs 写层分层、五要素↔UModel kinds 契约映射表、红线(不 vendor Go 源码 / 不用 SPL 替 OQL / 治理写不进 UModel)
- [x] 6.2 README 互链:在分层章节补一句"读层由 UModel 承担"的指向,并接 `docs/04`
- [x] 6.3 确认 `check_kernel_purity.py` 对 `umodel.py` 通过;solved 后 `openspec validate add-umodel-interop` 仍 valid

## 7. 收尾

- [x] 7.1 全量 `python -m pytest tests/ -q` + 新增 smoke 全绿
- [x] 7.2 `openspec validate add-umodel-interop --strict`;准备归档
