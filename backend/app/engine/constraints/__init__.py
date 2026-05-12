"""
约束系统

包含排课的硬约束和软约束检查。
"""

from .base import (
    ConstraintType,
    ViolationSeverity,
    ConstraintViolation,
    ConstraintCheckResult,
    Constraint,
    HardConstraint,
    SoftConstraint,
    ConstraintChecker
)

from .hard import (
    TeacherConflictConstraint,
    ClassConflictConstraint,
    TeacherAvailabilityConstraint,
    ContinuousBreakConstraint,
    VenueCapacityConstraint,
    LayerSyncConstraint,
    PeriodBoundaryConstraint,
    FirstPeriodConstraint,
    ElectivePeriodConstraint,
    DailySubjectLimitConstraint,
    create_default_hard_constraints
)

from .soft import (
    MainSubjectMorningConstraint,
    DistributionBalanceConstraint,
    TeacherConcentrationConstraint,
    ContinuousIntegrityConstraint,
    NoConsecutiveSameSubjectConstraint,
    PreferredPeriodConstraint,
    create_default_soft_constraints
)


def create_default_checker(venue_capacities: dict = None) -> ConstraintChecker:
    """
    创建默认配置的约束检查器
    
    Args:
        venue_capacities: 场地容量配置
    
    Returns:
        ConstraintChecker: 配置好的约束检查器
    """
    checker = ConstraintChecker()
    
    # 添加硬约束
    for constraint in create_default_hard_constraints(venue_capacities):
        checker.add_hard_constraint(constraint)
    
    # 添加软约束
    for constraint in create_default_soft_constraints():
        checker.add_soft_constraint(constraint)
    
    return checker


__all__ = [
    # 基类
    'ConstraintType',
    'ViolationSeverity',
    'ConstraintViolation',
    'ConstraintCheckResult',
    'Constraint',
    'HardConstraint',
    'SoftConstraint',
    'ConstraintChecker',
    # 硬约束
    'TeacherConflictConstraint',
    'ClassConflictConstraint',
    'TeacherAvailabilityConstraint',
    'ContinuousBreakConstraint',
    'VenueCapacityConstraint',
    'LayerSyncConstraint',
    'PeriodBoundaryConstraint',
    'FirstPeriodConstraint',
    'ElectivePeriodConstraint',
    'DailySubjectLimitConstraint',
    'create_default_hard_constraints',
    # 软约束
    'MainSubjectMorningConstraint',
    'DistributionBalanceConstraint',
    'TeacherConcentrationConstraint',
    'ContinuousIntegrityConstraint',
    'NoConsecutiveSameSubjectConstraint',
    'PreferredPeriodConstraint',
    'create_default_soft_constraints',
    # 便捷函数
    'create_default_checker',
]
