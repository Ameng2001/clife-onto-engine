"""NebulaGraph GraphStore 适配器（薄 adapter，跑在官方 nebula3-python 上）。

不重造图引擎，只把 GraphStore SPI 翻译为 nGQL。

**多本体/租户隔离**：一个 ontology_id ↔ 一个 NebulaGraph **space**；跨 space 默认零可见。
**存储模型（第一版）**：VID = 业务主键；每个 Object 类型 → TAG，每个 Link 类型 → EDGE，
各带一个 JSON `props` 列（schemaless 友好，OQL 不改即可跑）。按映射注册表落原生列是后续优化。

依赖未安装时 import 本模块不报错；实例化才校验，保持内核零硬依赖。
本模块与行业无关（CI 强制）。
"""
from __future__ import annotations

import json
import time
from typing import Iterator, Optional

from . import NeighborHit, StagedLink


def _lit(s: str) -> str:
    """安全的 nGQL 双引号字符串字面量（转义反斜杠与引号）。"""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


class NebulaGraphStore:
    """实现 GraphStore SPI。space = ontology_id。"""

    def __init__(self, *, ontology_id: str, registry, hosts=(("127.0.0.1", 9669),),
                 user: str = "root", password: str = "nebula") -> None:
        self.ontology_id = ontology_id          # = space 名
        self._registry = registry                # 解析 TAG/EDGE/邻居类型
        self._hosts = list(hosts)
        self._user = user
        self._password = password
        self._pool = None
        self._session = None

    # ---- 连接 ----
    def connect(self) -> "NebulaGraphStore":
        from nebula3.gclient.net import ConnectionPool
        from nebula3.Config import Config

        cfg = Config()
        cfg.max_connection_pool_size = 10
        self._pool = ConnectionPool()
        if not self._pool.init(self._hosts, cfg):
            raise RuntimeError(f"NebulaGraph 连接失败: {self._hosts}")
        self._session = self._pool.get_session(self._user, self._password)
        return self

    def close(self) -> None:
        if self._session:
            self._session.release()
        if self._pool:
            self._pool.close()

    def _exec(self, stmt: str):
        res = self._session.execute(stmt)
        if not res.is_succeeded():
            raise RuntimeError(f"nGQL 失败: {res.error_msg()} | {stmt}")
        return res

    def _use(self) -> None:
        self._exec(f"USE {self.ontology_id}")

    # ---- 建库建模（DDL 异步，含心跳等待）----
    def bootstrap(self, *, drop: bool = False, wait: float = 8.0) -> None:
        ns = self.ontology_id
        # 1. 注册存储节点（幂等；已注册会报错，忽略）
        try:
            self._exec('ADD HOSTS "storaged0":9779')
        except RuntimeError:
            pass
        self._wait_storage_online()
        # 2. 建 space（DDL 异步，轮询到可 USE 为止，避免 SpaceNotFound 竞态）
        if drop:
            self._exec(f"DROP SPACE IF EXISTS {ns}")
            time.sleep(wait)
        self._exec(f"CREATE SPACE IF NOT EXISTS {ns}(vid_type=FIXED_STRING(128))")
        self._wait_space()
        # 3. 建 TAG / EDGE
        for (o_ns, name) in self._registry.objects:
            if o_ns == ns:
                self._exec(f"CREATE TAG IF NOT EXISTS {name}(props string)")
        for (l_ns, name) in self._registry.links:
            if l_ns == ns:
                self._exec(f"CREATE EDGE IF NOT EXISTS {name}(props string)")
        time.sleep(wait)
        # 4. TAG 存在性索引（支撑 LOOKUP 扫描）；轮询到索引可用为止
        tags = [name for (o_ns, name) in self._registry.objects if o_ns == ns]
        for name in tags:
            self._exec(f"CREATE TAG INDEX IF NOT EXISTS i_{name} ON {name}()")
        self._wait_indexes(tags)
        self._use()

    def _wait_indexes(self, tags, retries: int = 30, interval: float = 2.0) -> None:
        self._use()
        for tag in tags:
            for _ in range(retries):
                res = self._session.execute(f"LOOKUP ON {tag} YIELD id(vertex) AS vid | LIMIT 1")
                if res.is_succeeded():
                    break
                time.sleep(interval)
            else:
                raise RuntimeError(f"tag index for {tag} 未就绪（LOOKUP 持续失败）")

    def _wait_space(self, retries: int = 30, interval: float = 2.0) -> None:
        for _ in range(retries):
            res = self._session.execute(f"USE {self.ontology_id}")
            if res.is_succeeded():
                return
            time.sleep(interval)
        raise RuntimeError(f"space {self.ontology_id} 未就绪（USE 持续失败）")

    def _wait_storage_online(self, retries: int = 30, interval: float = 2.0) -> None:
        for _ in range(retries):
            res = self._session.execute("SHOW HOSTS")
            if res.is_succeeded() and "ONLINE" in str(res):
                return
            time.sleep(interval)
        raise RuntimeError("storaged 未上线（SHOW HOSTS 无 ONLINE）")

    # ---- GraphStore SPI ----
    def get_object(self, object_type: str, key: str) -> Optional[dict]:
        self._use()
        res = self._exec(
            f"FETCH PROP ON {object_type} {_lit(key)} "
            f"YIELD properties(vertex).props AS props"
        )
        if res.row_size() == 0:
            return None
        vw = res.row_values(0)[0]
        return json.loads(vw.as_string()) if vw.is_string() else None

    def iter_objects(self, object_type: str) -> Iterator[tuple[str, dict]]:
        self._use()
        res = self._exec(
            f"LOOKUP ON {object_type} YIELD id(vertex) AS vid, properties(vertex).props AS props"
        )
        for i in range(res.row_size()):
            row = res.row_values(i)
            vid = row[0].as_string()
            props = json.loads(row[1].as_string()) if row[1].is_string() else {}
            yield vid, props

    def put_object(self, object_type: str, key: str, data: dict) -> None:
        self._use()
        blob = _lit(json.dumps(data, ensure_ascii=False))
        self._exec(f"INSERT VERTEX {object_type}(props) VALUES {_lit(key)}:({blob})")

    def put_link(self, link: StagedLink) -> None:
        self._use()
        blob = _lit(json.dumps(link.props, ensure_ascii=False))
        self._exec(
            f"INSERT EDGE {link.link_type}(props) "
            f"VALUES {_lit(link.from_key)}->{_lit(link.to_key)}:({blob})"
        )

    def search_around(self, object_type, key, link_type, *, direction="out") -> list[NeighborHit]:
        self._use()
        link = self._registry.links[(self.ontology_id, link_type)]
        neighbor_tag = link.to_type if direction == "out" else link.from_type
        rev = " REVERSELY" if direction == "in" else ""
        edge_fn = "dst(edge)" if direction == "out" else "src(edge)"
        res = self._exec(
            f"GO FROM {_lit(key)} OVER {link_type}{rev} "
            f"YIELD {edge_fn} AS nvid, properties(edge).props AS eprops"
        )
        hits: list[NeighborHit] = []
        for i in range(res.row_size()):
            row = res.row_values(i)
            nvid = row[0].as_string()
            eprops = json.loads(row[1].as_string()) if row[1].is_string() else {}
            node = self.get_object(neighbor_tag, nvid) or {}
            hits.append(NeighborHit(neighbor_tag, nvid, node, eprops))
        return hits
