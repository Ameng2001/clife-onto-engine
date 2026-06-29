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
import re
import time
from typing import Iterator, Optional

from . import NeighborHit, StagedLink

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")  # nGQL 列标识符；非 ASCII 名不落原生列


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
        # 3. 建 TAG（原生列 + props blob）/ EDGE
        #    原生列由映射注册表声明（columns），落成真列才能建索引、做 WHERE 谓词下推。
        for (o_ns, name) in self._registry.objects:
            if o_ns == ns:
                cols = self._native_columns(name)
                col_defs = "".join(f"{c} string, " for c in cols)  # 原生列默认 string
                self._exec(f"CREATE TAG IF NOT EXISTS {name}({col_defs}props string)")
        for (l_ns, name) in self._registry.links:
            if l_ns == ns:
                self._exec(f"CREATE EDGE IF NOT EXISTS {name}(props string)")
        time.sleep(wait)
        # 4. 索引：存在性索引（LOOKUP 全扫）+ 原生列索引（WHERE 谓词下推走索引）
        tags = [name for (o_ns, name) in self._registry.objects if o_ns == ns]
        for name in tags:
            self._exec(f"CREATE TAG INDEX IF NOT EXISTS i_{name} ON {name}()")
            cols = self._native_columns(name)
            if cols:
                col_idx = ", ".join(f"{c}(64)" for c in cols)
                self._exec(f"CREATE TAG INDEX IF NOT EXISTS i_{name}_cols ON {name}({col_idx})")
        self._wait_indexes(tags)
        self._wait_writable(tags)   # 冷启动：等 graphd 写 schema 缓存就绪，首次 INSERT 才不报 No schema
        self._use()

    def _wait_writable(self, tags, retries: int = 30, interval: float = 2.0) -> None:
        """写探针：轮询到每个 tag 真能 INSERT 为止（绕过 DDL→graphd 写缓存传播延迟）。"""
        self._use()
        for tag in tags:
            for _ in range(retries):
                res = self._session.execute(f'INSERT VERTEX {tag}(props) VALUES "__probe__":("probe")')
                if res.is_succeeded():
                    self._session.execute('DELETE VERTEX "__probe__"')
                    break
                time.sleep(interval)
            else:
                raise RuntimeError(f"tag {tag} 不可写（INSERT 探针持续失败）")

    def _native_columns(self, object_type: str) -> list:
        m = self._registry.mappings.get_object(self.ontology_id, object_type)
        if not m:
            return []
        # 仅 ASCII 标识符落成原生列（可索引、可 WHERE）；非 ASCII 字段留在 props blob。
        return [c for c in m.primary.columns if _IDENT.match(c)]

    def _wait_indexes(self, tags, retries: int = 30, interval: float = 2.0) -> None:
        self._use()
        for tag in tags:
            # 存在性索引（LOOKUP 全扫）
            self._wait_lookup(f"LOOKUP ON {tag} YIELD id(vertex) AS vid | LIMIT 1", tag, retries, interval)
            # 原生列索引（WHERE 谓词下推走索引）——就绪后 find_where 才不回退全扫
            cols = self._native_columns(tag)
            if cols:
                probe = (f'LOOKUP ON {tag} WHERE {tag}.{cols[0]} == "__probe__" '
                         f"YIELD id(vertex) AS vid | LIMIT 1")
                self._wait_lookup(probe, f"{tag}.{cols[0]}", retries, interval)

    def _wait_lookup(self, stmt: str, what: str, retries: int = 30, interval: float = 2.0) -> None:
        for _ in range(retries):
            if self._session.execute(stmt).is_succeeded():
                return
            time.sleep(interval)
        raise RuntimeError(f"index for {what} 未就绪（LOOKUP 持续失败）")

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
        cols = [c for c in self._native_columns(object_type) if c in data]
        blob = _lit(json.dumps(data, ensure_ascii=False))
        names = ", ".join(["props"] + cols)
        vals = ", ".join([blob] + [_lit(str(data[c])) for c in cols])  # 原生列值存为 string
        self._exec(f"INSERT VERTEX {object_type}({names}) VALUES {_lit(key)}:({vals})")

    def put_link(self, link: StagedLink) -> None:
        self._use()
        blob = _lit(json.dumps(link.props, ensure_ascii=False))
        self._exec(
            f"INSERT EDGE {link.link_type}(props) "
            f"VALUES {_lit(link.from_key)}->{_lit(link.to_key)}:({blob})"
        )

    def delete_object(self, object_type: str, key: str) -> None:
        self._use()
        # DELETE VERTEX 连带删除其边；补偿场景下用于撤销本次新建的顶点
        self._exec(f"DELETE VERTEX {_lit(key)} WITH EDGE")

    def delete_link(self, link: StagedLink) -> None:
        self._use()
        self._exec(
            f"DELETE EDGE {link.link_type} {_lit(link.from_key)} -> {_lit(link.to_key)}"
        )

    _SYM = {"eq": "==", "ne": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<="}

    def find_where(self, object_type: str, conditions: list) -> list[dict]:
        """谓词下推：把能下推的条件（原生列 + 字符串值 + 比较算子）编译进 nGQL WHERE，
        让 NebulaGraph 走索引在库内过滤；其余条件由调用方（OQL）再校验。下推失败则回退全扫。"""
        self._use()
        cols = set(self._native_columns(object_type))
        pushable = [(f, op, v) for (f, op, v) in conditions
                    if f in cols and op in self._SYM and isinstance(v, str)]
        try:
            if pushable:
                where = " AND ".join(
                    f"{object_type}.{f} {self._SYM[op]} {_lit(v)}" for f, op, v in pushable)
                res = self._exec(
                    f"LOOKUP ON {object_type} WHERE {where} YIELD properties(vertex).props AS props")
            else:
                res = self._exec(
                    f"LOOKUP ON {object_type} YIELD properties(vertex).props AS props")
            out = []
            for i in range(res.row_size()):
                vw = res.row_values(i)[0]
                out.append(json.loads(vw.as_string()) if vw.is_string() else {})
            return out
        except RuntimeError:
            # 下推失败（索引未就绪/不支持）→ 回退全扫，OQL 再校验，正确性不受影响
            return [row for _, row in self.iter_objects(object_type)]

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
