"""
软约束评分

软约束是尽量满足的约束，不满足不会导致排课失败，但会影响评分。
"""

from typing import List, Dict, TYPE_CHECKING
from collections import defaultdict
from .base import (
    SoftConstraint, ConstraintCheckResult, ConstraintViolation, ViolationSeverity
)

if TYPE_CHECKING:
    from ..data.models import ScheduleData, ScheduleRecord


class MainSubjectMorningConstraint(SoftConstraint):
    """
    主科上午优先约束
    
    主科（语数英）应尽量安排在上午。
    """
    
    MORNING_PERIODS = [1, 2, 3, 4]  # 上午节次
    
    def __init__(self, weight: float = 0.3):
        super().__init__("SOFT_001", "主科上午优先", weight)
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        subject = data.get_subject(record.subject_id)
        if not subject or not subject.is_main:
            # 非主科不检查
            result.score = 1.0
            return result
        
        # 检查是否在上午
        if record.period in self.MORNING_PERIODS:
            result.score = 1.0
        else:
            result.score = 0.5  # 下午安排扣分
            violation = self.create_violation(
                f"主科{subject.name}安排在下午（第{record.period}节）",
                severity=ViolationSeverity.INFO,
                subject_name=subject.name,
                period=record.period
            )
            result.add_violation(violation)
        
        return result


class DistributionBalanceConstraint(SoftConstraint):
    """
    课时分布均衡约束
    
    每天的课时应尽量均匀分布，避免某天课太多。
    """
    
    def __init__(self, weight: float = 0.2):
        super().__init__("SOFT_002", "课时分布均衡", weight)
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 统计该班级每天的课时数
        class_daily_hours = defaultdict(int)
        class_daily_hours[record.day] += record.duration
        
        for existing in existing_records:
            if existing.class_id == record.class_id:
                class_daily_hours[existing.day] += existing.duration
        
        # 计算标准差
        if len(class_daily_hours) < 2:
            result.score = 1.0
            return result
        
        hours = list(class_daily_hours.values())
        mean = sum(hours) / len(hours)
        variance = sum((h - mean) ** 2 for h in hours) / len(hours)
        std_dev = variance ** 0.5
        
        # 标准差越小越好，超过1.5开始扣分
        if std_dev <= 1.0:
            result.score = 1.0
        elif std_dev <= 2.0:
            result.score = 0.8
        elif std_dev <= 3.0:
            result.score = 0.5
            violation = self.create_violation(
                f"课时分布不均衡（标准差{std_dev:.1f}）",
                severity=ViolationSeverity.WARNING,
                std_dev=std_dev
            )
            result.add_violation(violation)
        else:
            result.score = 0.3
            violation = self.create_violation(
                f"课时分布严重不均衡（标准差{std_dev:.1f}）",
                severity=ViolationSeverity.WARNING,
                std_dev=std_dev
            )
            result.add_violation(violation)
        
        return result


class TeacherConcentrationConstraint(SoftConstraint):
    """
    教师课程集中约束
    
    同一教师的课程应尽量集中，减少零散时间。
    """
    
    def __init__(self, weight: float = 0.2):
        super().__init__("SOFT_003", "教师课程集中", weight)
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 获取该教师当天的课程
        teacher_today = [record]
        for existing in existing_records:
            if existing.teacher_id == record.teacher_id and existing.day == record.day:
                teacher_today.append(existing)
        
        if len(teacher_today) < 2:
            result.score = 1.0
            return result
        
        # 计算课程之间的空档
        periods = []
        for r in teacher_today:
            periods.extend(r.periods)
        
        periods.sort()
        
        # 计算空档数
        gaps = 0
        for i in range(len(periods) - 1):
            gap = periods[i + 1] - periods[i] - 1
            if gap > 0:
                # 跨午休的空档不算
                if not (periods[i] <= 4 and periods[i + 1] >= 5):
                    gaps += gap
        
        # 空档越少越好
        if gaps == 0:
            result.score = 1.0
        elif gaps == 1:
            result.score = 0.9
        elif gaps == 2:
            result.score = 0.7
        else:
            result.score = 0.5
            teacher = data.get_teacher(record.teacher_id)
            teacher_name = teacher.name if teacher else f"教师{record.teacher_id}"
            violation = self.create_violation(
                f"{teacher_name}在周{record.day}有{gaps}个空档",
                severity=ViolationSeverity.INFO,
                teacher_id=record.teacher_id,
                day=record.day,
                gaps=gaps
            )
            result.add_violation(violation)
        
        return result


class ContinuousIntegrityConstraint(SoftConstraint):
    """
    连堂完整性约束
    
    需要连堂的课程应该完整连堂。
    """
    
    def __init__(self, weight: float = 0.15):
        super().__init__("SOFT_004", "连堂完整性", weight)
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        task = data.get_task(record.task_id)
        if not task or not task.is_continuous:
            result.score = 1.0
            return result
        
        # 检查是否达到要求的连堂节数
        if record.duration >= task.continuous_count:
            result.score = 1.0
        else:
            result.score = 0.5
            violation = self.create_violation(
                f"{task.subject_name}需要连堂{task.continuous_count}节，实际只有{record.duration}节",
                severity=ViolationSeverity.WARNING,
                task_id=task.id,
                required=task.continuous_count,
                actual=record.duration
            )
            result.add_violation(violation)
        
        return result


class NoConsecutiveSameSubjectConstraint(SoftConstraint):
    """
    同科目不连续约束
    
    同一班级的同一科目不应该在相邻节次连续出现（除非是连堂课）。
    """
    
    def __init__(self, weight: float = 0.15):
        super().__init__("SOFT_005", "同科目不连续", weight)
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 检查是否与相邻节次的同科目课程冲突
        for existing in existing_records:
            # 同班级同科目同一天
            if (existing.class_id == record.class_id and 
                existing.subject_id == record.subject_id and
                existing.day == record.day):
                
                # 检查是否是同一任务的连堂
                if existing.task_id == record.task_id:
                    continue
                
                # 检查是否相邻
                existing_periods = set(existing.periods)
                record_periods = set(record.periods)
                
                for ep in existing_periods:
                    for rp in record_periods:
                        if abs(ep - rp) == 1:
                            # 跨午休不算相邻
                            if not ((ep == 4 and rp == 5) or (ep == 5 and rp == 4)):
                                subject = data.get_subject(record.subject_id)
                                subject_name = subject.name if subject else f"科目{record.subject_id}"
                                
                                violation = self.create_violation(
                                    f"{subject_name}在周{record.day}连续出现（第{ep}和{rp}节）",
                                    severity=ViolationSeverity.INFO,
                                    subject_id=record.subject_id,
                                    day=record.day
                                )
                                result.add_violation(violation)
                                result.score = 0.7
                                return result
        
        result.score = 1.0
        return result


class PreferredPeriodConstraint(SoftConstraint):
    """
    优先时段约束
    
    课程应尽量安排在其偏好的时段。
    """
    
    MORNING_PERIODS = [1, 2, 3, 4]
    AFTERNOON_PERIODS = [5, 6, 7, 8, 9]
    
    def __init__(self, weight: float = 0.1):
        super().__init__("SOFT_006", "优先时段", weight)
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        task = data.get_task(record.task_id)
        if not task or task.preferred_period == "ANY":
            result.score = 1.0
            return result
        
        is_morning = record.period in self.MORNING_PERIODS
        
        if task.preferred_period == "MORNING" and is_morning:
            result.score = 1.0
        elif task.preferred_period == "AFTERNOON" and not is_morning:
            result.score = 1.0
        else:
            result.score = 0.7
            violation = self.create_violation(
                f"{task.subject_name}偏好{task.preferred_period}，实际安排在{'上午' if is_morning else '下午'}",
                severity=ViolationSeverity.INFO,
                task_id=task.id,
                preferred=task.preferred_period,
                actual="MORNING" if is_morning else "AFTERNOON"
            )
            result.add_violation(violation)
        
        return result


def create_default_soft_constraints() -> List[SoftConstraint]:
    """
    创建默认的软约束列表
    
    Returns:
        List[SoftConstraint]: 软约束列表
    """
    return [
        MainSubjectMorningConstraint(weight=0.3),
        DistributionBalanceConstraint(weight=0.2),
        TeacherConcentrationConstraint(weight=0.2),
        ContinuousIntegrityConstraint(weight=0.15),
        NoConsecutiveSameSubjectConstraint(weight=0.1),
        PreferredPeriodConstraint(weight=0.05),
    ]
