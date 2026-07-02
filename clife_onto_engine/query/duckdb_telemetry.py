"""DuckDB 遥测执行器 —— 真后端出值，却零服务器（嵌入式、进程内）。

`TelemetryExecutor` 协议的一个真实现：执行 `build_plan` 产出的**已代入 SQL**（provider=sql），
在嵌入式 DuckDB 上真跑出值。与离线默认 `InMemoryTelemetryExecutor` 同协议——Session 换执行器无感。

分层纪律不变：引擎（build_plan）只产计划；执行器是调用方侧组件。防注入在 build_plan
（label 白名单，元字符一律拒），执行器只跑**受信模板**的已代入 SQL。行业无关（CI 强制）。

  ex = DuckDBTelemetryExecutor()                 # 内存库；或传 database=路径 / conn=已有连接
  ex.conn.execute("CREATE TABLE ... ")           # 准备遥测数据（真部署由采集管道落库）
  Session(..., telemetry_executor=ex)            # ask("墒情多少") 端到端出值
"""
from __future__ import annotations

from typing import Optional


class DuckDBTelemetryExecutor:
    def __init__(self, conn=None, *, database: str = ":memory:") -> None:
        if conn is None:
            import duckdb  # 延迟导入：未装 duckdb 时不影响引擎其它部分
            conn = duckdb.connect(database)
        self._conn = conn

    @property
    def conn(self):
        """暴露连接供建表/灌数（真部署由采集管道写；测试/demo 就地建）。"""
        return self._conn

    def execute(self, plan: dict) -> dict:
        if not plan.get("ok"):
            return plan
        sql = plan["plan"]
        try:
            rows = self._conn.execute(sql).fetchall()
        except Exception as e:  # SQL/表缺失等 → 结构化错误，不崩
            return {"ok": False, "error": f"duckdb 执行失败: {type(e).__name__}: {e}"}
        out: dict = {"ok": True, "provider": plan.get("provider"), "kind": plan.get("kind"), "plan": sql}
        if plan.get("kind") == "metric":
            out["value"] = rows[0][0] if rows and rows[0] else None
        else:
            out["points"] = [list(r) for r in rows]
        return out
