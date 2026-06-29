"""SPI 与内核异常。"""
from __future__ import annotations


class OntoEngineError(Exception):
    """内核基类异常。"""


class RegistrationError(OntoEngineError):
    """插件注册冲突或非法（重复名、未知引用）。"""


class ResolutionError(OntoEngineError):
    """运行时无法解析 Action / Rule / Function。"""


class CapabilityError(OntoEngineError):
    """插件代码尝试超越 ctx 授予的受限能力（如直接写库、跨租户访问）。"""


class CommitError(OntoEngineError):
    """提交期后端写入失败。引擎已对已写入部分做确定性补偿回滚。"""

    def __init__(self, message: str, *, applied: int = 0) -> None:
        super().__init__(message)
        self.applied = applied  # 失败前已写入并已被补偿撤销的操作数
