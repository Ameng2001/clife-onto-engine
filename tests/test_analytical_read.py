"""遥测读 Profile B（数仓/分析读）：语义指标 → 数仓 SQL 计划 → DuckDB 维度化聚合 + 防注入。"""
from __future__ import annotations

import pytest

from clife_onto_engine.query.telemetry import build_analytical_plan
from clife_onto_engine.sdk import spi

import plugins.grass  # noqa: F401

duckdb = pytest.importorskip("duckdb")
from clife_onto_engine.query.duckdb_telemetry import DuckDBTelemetryExecutor  # noqa: E402


def test_semantic_metric_compiles_to_warehouse_sql():
    plan = build_analytical_plan(spi.registry, "grass", "退化趋势", params={"region": "巴彦淖尔"})
    assert plan["ok"] and plan["kind"] == "analytical" and plan["dimensions"] == ["year"]
    assert plan["plan"] == ("SELECT year, avg(coverage) AS coverage FROM rs_monitor "
                            "WHERE region = '巴彦淖尔' GROUP BY year ORDER BY year")


def test_count_metric_no_field():
    plan = build_analytical_plan(spi.registry, "grass", "区域地块数", params={"region": "乌兰察布"})
    assert plan["plan"] == "SELECT count(*) AS count FROM geo_parcel WHERE region = '乌兰察布'"


def test_analytical_plan_runs_on_duckdb_dimensioned():
    ex = DuckDBTelemetryExecutor()
    ex.conn.execute("CREATE TABLE rs_monitor(region VARCHAR, year INT, coverage DOUBLE)")
    ex.conn.execute("INSERT INTO rs_monitor VALUES "
                    "('巴彦淖尔',2023,0.40),('巴彦淖尔',2023,0.44),"
                    "('巴彦淖尔',2024,0.52),('乌兰察布',2024,0.90)")
    plan = build_analytical_plan(spi.registry, "grass", "退化趋势", params={"region": "巴彦淖尔"})
    out = ex.execute(plan)
    assert out["ok"] and out["kind"] == "analytical"
    # 维度化结果：按 year 分组，巴彦淖尔 2023=avg(0.40,0.44)=0.42、2024=0.52（乌兰察布未混入）
    assert [[y, round(c, 3)] for y, c in out["points"]] == [[2023, 0.42], [2024, 0.52]]


def test_anti_injection_on_filter_value():
    bad = build_analytical_plan(spi.registry, "grass", "退化趋势",
                                params={"region": "x'; DROP TABLE rs_monitor;--"})
    assert bad["ok"] is False and "防注入" in bad["error"]


def test_missing_placeholder_and_unknown_metric():
    assert build_analytical_plan(spi.registry, "grass", "退化趋势", params={})["ok"] is False
    assert build_analytical_plan(spi.registry, "grass", "不存在", params={})["ok"] is False
