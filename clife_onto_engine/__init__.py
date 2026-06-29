"""clife-onto-engine —— 与行业无关的数智本体运行时内核。

行业本体以插件（plugins/<industry>/）形态接入，租户配置（tenants/<customer>/）注入私有实例。
内核只理解元模型五要素：Object / Link / Function / Rule / Action。

红线：本包内不得出现任何行业词汇（CI 强制，见 scripts/check_kernel_purity.py）。
"""
from __future__ import annotations

__version__ = "0.1.0"

from .kernel import ActionEngine, ActionPreview, ActionResult, StructuredRejection, Violation
from .session import Reply, Session

__all__ = [
    "ActionEngine",
    "ActionResult",
    "ActionPreview",
    "StructuredRejection",
    "Violation",
    "Session",
    "Reply",
    "__version__",
]
