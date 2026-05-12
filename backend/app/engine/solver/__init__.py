"""
基于 OR-Tools CP-SAT 的排课求解器

使用 Google OR-Tools 的 CP-SAT 约束满足求解器替代
手写的贪心 + 模拟退火算法，实现可靠的排课求解。
"""

from .cp_solver import (
    CPScheduleSolver, ScheduleSession, SessionBuilder, DEFAULT_SOFT_CONFIG,
)

__all__ = [
    'CPScheduleSolver',
    'ScheduleSession',
    'SessionBuilder',
    'DEFAULT_SOFT_CONFIG',
]
