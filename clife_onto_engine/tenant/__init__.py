"""租户数据接入 —— 把租户声明的数据源按本体 schema 校验后落库。与行业无关（CI 强制）。"""
from .ingest import IngestReport, ObjectIngest, load_tenant

__all__ = ["load_tenant", "IngestReport", "ObjectIngest"]
