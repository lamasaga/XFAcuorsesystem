"""
约束系统基类

定义约束检查的基本接口和通用功能。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..data.models import ScheduleData, ScheduleRecord


class ConstraintType(Enum):
    """约束类型"""
    HARD = "hard"  # 硬约束（必须满足）
    SOFT = "soft"  # 软约束（尽量满足）


class ViolationSeverity(Enum):
    """违反严重程度"""
    CRITICAL = "critical"  # 严重（导致无效）
    WARNING = "warning"    # 警告（影响评分）
    INFO = "info"          # 提示


@dataclass
class ConstraintViolation:
    """
    约束违反记录
    
    Attributes:
        constraint_id: 约束ID
        constraint_name: 约束名称
        message: 违反描述
        severity: 严重程度
        details: 详细信息
    """
    constraint_id: str
    constraint_name: str
    message: str
    severity: ViolationSeverity = ViolationSeverity.WARNING
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.constraint_name}: {self.message}"


@dataclass
class ConstraintCheckResult:
    """
    约束检查结果
    
    Attributes:
        passed: 是否通过
        violations: 违反列表
        score: 得分（软约束）
    """
    passed: bool = True
    violations: List[ConstraintViolation] = field(default_factory=list)
    score: float = 1.0  # 1.0 表示完全满足
    
    def add_violation(self, violation: ConstraintViolation):
        """添加违反记录"""
        self.violations.append(violation)
        if violation.severity == ViolationSeverity.CRITICAL:
            self.passed = False
    
    @property
    def is_valid(self) -> bool:
        """是否有效（没有严重违反）"""
        return all(v.severity != ViolationSeverity.CRITICAL for v in self.violations)
    
    def merge(self, other: 'ConstraintCheckResult'):
        """合并另一个检查结果"""
        self.passed = self.passed and other.passed
        self.violations.extend(other.violations)
        self.score = min(self.score, other.score)


class Constraint(ABC):
    """
    约束基类
    
    所有约束检查器都应继承此类。
    """
    
    def __init__(self, constraint_id: str, name: str, constraint_type: ConstraintType):
        self.constraint_id = constraint_id
        self.name = name
        self.constraint_type = constraint_type
    
    @abstractmethod
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        """
        检查约束
        
        Args:
            record: 要检查的排课记录
            existing_records: 已有的排课记录
            data: 完整的排课数据
        
        Returns:
            ConstraintCheckResult: 检查结果
        """
        pass
    
    def create_violation(
        self,
        message: str,
        severity: ViolationSeverity = ViolationSeverity.WARNING,
        **details
    ) -> ConstraintViolation:
        """创建违反记录"""
        return ConstraintViolation(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            message=message,
            severity=severity,
            details=details
        )


class HardConstraint(Constraint):
    """硬约束基类"""
    
    def __init__(self, constraint_id: str, name: str):
        super().__init__(constraint_id, name, ConstraintType.HARD)


class SoftConstraint(Constraint):
    """软约束基类"""
    
    def __init__(self, constraint_id: str, name: str, weight: float = 1.0):
        super().__init__(constraint_id, name, ConstraintType.SOFT)
        self.weight = weight  # 约束权重


class ConstraintChecker:
    """
    约束检查器（聚合所有约束）
    
    Usage:
        checker = ConstraintChecker()
        checker.add_hard_constraint(TeacherConflictConstraint())
        checker.add_soft_constraint(MainSubjectMorningConstraint(), weight=0.3)
        
        result = checker.check(record, existing_records, data)
    """
    
    def __init__(self):
        self.hard_constraints: List[HardConstraint] = []
        self.soft_constraints: List[SoftConstraint] = []
    
    def add_hard_constraint(self, constraint: HardConstraint):
        """添加硬约束"""
        self.hard_constraints.append(constraint)
    
    def add_soft_constraint(self, constraint: SoftConstraint, weight: float = None):
        """添加软约束"""
        if weight is not None:
            constraint.weight = weight
        self.soft_constraints.append(constraint)
    
    def check_hard(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        """只检查硬约束"""
        result = ConstraintCheckResult()
        
        for constraint in self.hard_constraints:
            check_result = constraint.check(record, existing_records, data)
            result.merge(check_result)
            
            # 硬约束一旦失败，立即返回
            if not result.passed:
                return result
        
        return result
    
    def check_soft(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        """只检查软约束"""
        result = ConstraintCheckResult()
        
        total_weight = sum(c.weight for c in self.soft_constraints)
        weighted_score = 0.0
        
        for constraint in self.soft_constraints:
            check_result = constraint.check(record, existing_records, data)
            result.violations.extend(check_result.violations)
            weighted_score += check_result.score * constraint.weight
        
        if total_weight > 0:
            result.score = weighted_score / total_weight
        
        return result
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        """检查所有约束"""
        # 先检查硬约束
        hard_result = self.check_hard(record, existing_records, data)
        if not hard_result.passed:
            return hard_result
        
        # 再检查软约束
        soft_result = self.check_soft(record, existing_records, data)
        
        # 合并结果
        hard_result.merge(soft_result)
        return hard_result
    
    def is_valid_placement(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> bool:
        """快速检查是否可以放置（只检查硬约束）"""
        return self.check_hard(record, existing_records, data).passed
