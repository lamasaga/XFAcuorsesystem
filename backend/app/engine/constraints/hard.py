"""
硬约束检测

硬约束是必须满足的约束，违反则排课无效。
"""

from typing import List, Dict, Set, TYPE_CHECKING
from .base import (
    HardConstraint, ConstraintCheckResult, ConstraintViolation, ViolationSeverity
)

if TYPE_CHECKING:
    from ..data.models import ScheduleData, ScheduleRecord


class TeacherConflictConstraint(HardConstraint):
    """
    教师时间冲突约束
    
    同一教师在同一时间只能上一节课。
    """
    
    def __init__(self):
        super().__init__("HARD_001", "教师时间冲突")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 获取该记录占用的所有时间槽
        record_periods = set(record.periods)
        
        for existing in existing_records:
            # 同一教师
            if existing.teacher_id == record.teacher_id:
                # 同一天
                if existing.day == record.day:
                    # 检查时间是否重叠
                    existing_periods = set(existing.periods)
                    overlap = record_periods & existing_periods
                    
                    if overlap:
                        teacher = data.get_teacher(record.teacher_id)
                        teacher_name = teacher.name if teacher else f"教师{record.teacher_id}"
                        
                        violation = self.create_violation(
                            f"{teacher_name} 在周{record.day}第{list(overlap)[0]}节已有课程",
                            severity=ViolationSeverity.CRITICAL,
                            teacher_id=record.teacher_id,
                            day=record.day,
                            conflicting_periods=list(overlap)
                        )
                        result.add_violation(violation)
                        return result
        
        return result


class ClassConflictConstraint(HardConstraint):
    """
    班级时间冲突约束
    
    同一班级在同一时间只能上一节课。
    """
    
    def __init__(self):
        super().__init__("HARD_002", "班级时间冲突")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        record_periods = set(record.periods)
        
        for existing in existing_records:
            # 同一班级
            if existing.class_id == record.class_id:
                # 同一天
                if existing.day == record.day:
                    # 检查时间是否重叠
                    existing_periods = set(existing.periods)
                    overlap = record_periods & existing_periods
                    
                    if overlap:
                        cls = data.get_class(record.class_id)
                        class_name = cls.name if cls else f"班级{record.class_id}"
                        
                        violation = self.create_violation(
                            f"{class_name} 在周{record.day}第{list(overlap)[0]}节已有课程",
                            severity=ViolationSeverity.CRITICAL,
                            class_id=record.class_id,
                            day=record.day,
                            conflicting_periods=list(overlap)
                        )
                        result.add_violation(violation)
                        return result
        
        return result


class TeacherAvailabilityConstraint(HardConstraint):
    """
    教师可用性约束
    
    教师在其不可用时间不能排课。
    包括手动设置的不可用时间和班次（早晚班）导致的不可用时间。
    """
    
    def __init__(self):
        super().__init__("HARD_003", "教师不可用时间")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        teacher = data.get_teacher(record.teacher_id)
        if not teacher:
            return result
        
        for period in record.periods:
            # is_available 方法会同时检查 unavailable_slots 和 daily_shifts
            if not teacher.is_available(record.day, period):
                violation = self.create_violation(
                    f"{teacher.name} 在周{record.day}第{period}节不可用",
                    severity=ViolationSeverity.CRITICAL,
                    teacher_id=record.teacher_id,
                    day=record.day,
                    period=period
                )
                result.add_violation(violation)
                return result
        
        return result


class ContinuousBreakConstraint(HardConstraint):
    """
    连堂课午休边界约束
    
    连堂课不能跨越午休时间（第5节和第6节之间）。
    """
    
    LUNCH_BREAK_AFTER = 5  # 午休在第5节之后
    
    def __init__(self):
        super().__init__("HARD_004", "连堂课午休边界")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 只检查连堂课
        if record.duration <= 1:
            return result
        
        periods = record.periods
        
        # 检查是否跨越午休
        if self.LUNCH_BREAK_AFTER in periods and (self.LUNCH_BREAK_AFTER + 1) in periods:
            violation = self.create_violation(
                f"连堂课不能跨越午休时间（第{self.LUNCH_BREAK_AFTER}节和第{self.LUNCH_BREAK_AFTER + 1}节之间）",
                severity=ViolationSeverity.CRITICAL,
                day=record.day,
                periods=periods
            )
            result.add_violation(violation)
        
        return result


class VenueCapacityConstraint(HardConstraint):
    """
    场地容量约束
    
    同一时间同一类型场地的课程数不能超过场地容量。
    """
    
    def __init__(self, venue_capacities: Dict[str, int] = None):
        super().__init__("HARD_005", "场地容量限制")
        # 场地类型 -> 容量
        self.venue_capacities = venue_capacities or {}
    
    def set_capacities(self, capacities: Dict[str, int]):
        """设置场地容量"""
        self.venue_capacities = capacities
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 获取任务的场地需求
        task = data.get_task(record.task_id)
        if not task or not task.required_venue_type:
            return result
        
        venue_type = task.required_venue_type
        capacity = self.venue_capacities.get(venue_type, 1)
        
        # 如果没有设置容量，从数据中获取
        if venue_type not in self.venue_capacities:
            capacity = data.get_venue_capacity(venue_type)
        
        # 统计同一时间同类型场地的使用数
        record_periods = set(record.periods)
        
        for period in record_periods:
            count = 1  # 当前记录
            
            for existing in existing_records:
                if existing.day != record.day:
                    continue
                
                existing_task = data.get_task(existing.task_id)
                if not existing_task or existing_task.required_venue_type != venue_type:
                    continue
                
                if period in existing.periods:
                    count += 1
            
            if count > capacity:
                violation = self.create_violation(
                    f"{venue_type}在周{record.day}第{period}节已达容量上限({capacity})",
                    severity=ViolationSeverity.CRITICAL,
                    venue_type=venue_type,
                    day=record.day,
                    period=period,
                    capacity=capacity,
                    current_count=count
                )
                result.add_violation(violation)
                return result
        
        return result


class LayerSyncConstraint(HardConstraint):
    """
    分层课同步约束
    
    同一分层组的所有任务必须在相同的时间上课。
    """
    
    def __init__(self):
        super().__init__("HARD_006", "分层课同步")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 非分层课跳过
        if not record.layer_group_id:
            return result
        
        # 查找同一分层组的已排课程
        for existing in existing_records:
            if existing.layer_group_id != record.layer_group_id:
                continue
            
            # 同一分层组的课程必须在相同时间
            if existing.day != record.day or existing.period != record.period:
                violation = self.create_violation(
                    f"分层组{record.layer_group_id}的课程时间不一致",
                    severity=ViolationSeverity.CRITICAL,
                    layer_group_id=record.layer_group_id,
                    expected_day=existing.day,
                    expected_period=existing.period,
                    actual_day=record.day,
                    actual_period=record.period
                )
                result.add_violation(violation)
                return result
        
        return result


class PeriodBoundaryConstraint(HardConstraint):
    """
    节次边界约束
    
    课程不能超出一天的节次范围。
    - 常规：1-9节
    - G8/G9年级周四：1-11节
    - 周五：1-8节
    """
    
    # 最大节次配置
    MAX_PERIOD_REGULAR = 9   # 常规最大节次
    MAX_PERIOD_ELECTIVE = 11 # 含选修课的最大节次（G8/G9周四）
    MAX_PERIOD_FRIDAY = 8    # 周五最大节次
    
    ELECTIVE_DAY = 4  # 周四
    ELECTIVE_GRADES = ['G8', 'G9']
    
    def __init__(self):
        super().__init__("HARD_007", "节次边界")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 检查起始节次
        if record.period < 1:
            violation = self.create_violation(
                f"起始节次{record.period}无效，必须 >= 1",
                severity=ViolationSeverity.CRITICAL
            )
            result.add_violation(violation)
            return result
        
        # 根据班级年级和日期确定最大节次
        max_period = self.MAX_PERIOD_REGULAR
        
        cls = data.get_class(record.class_id)
        grade = cls.grade if cls else None
        
        if record.day == 5:
            # 周五
            max_period = self.MAX_PERIOD_FRIDAY
        elif record.day == self.ELECTIVE_DAY and grade in self.ELECTIVE_GRADES:
            # G8/G9年级周四
            max_period = self.MAX_PERIOD_ELECTIVE
        
        # 检查结束节次
        end_period = record.period + record.duration - 1
        if end_period > max_period:
            violation = self.create_violation(
                f"课程超出节次范围，结束于第{end_period}节（当前最大{max_period}节）",
                severity=ViolationSeverity.CRITICAL,
                day=record.day,
                grade=grade,
                max_period=max_period
            )
            result.add_violation(violation)
            return result
        
        return result


class FirstPeriodConstraint(HardConstraint):
    """
    第一节课限制约束
    
    早上第一节课不能上某些类型的课程（如艺体课）。
    """
    
    RESTRICTED_CATEGORIES = ["艺术", "体育"]
    
    def __init__(self):
        super().__init__("HARD_008", "第一节课限制")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 只检查第一节
        if record.period != 1:
            return result
        
        subject = data.get_subject(record.subject_id)
        if not subject:
            return result
        
        if subject.category in self.RESTRICTED_CATEGORIES:
            violation = self.create_violation(
                f"第一节课不能安排{subject.category}类课程（{subject.name}）",
                severity=ViolationSeverity.CRITICAL,
                subject_id=record.subject_id,
                subject_name=subject.name,
                category=subject.category
            )
            result.add_violation(violation)
        
        return result


class ElectivePeriodConstraint(HardConstraint):
    """
    选修课时段约束
    
    第10-11节是选修课时段，只有G8/G9年级周四可以用于正课排课。
    其他年级或其他时间的10-11节不能排正课。
    """
    
    # 选修课时段配置
    ELECTIVE_PERIODS = [10, 11]
    ELECTIVE_DAY = 4  # 周四
    ELECTIVE_GRADES = ['G8', 'G9']  # 可使用选修课时段的年级
    
    def __init__(self):
        super().__init__("HARD_009", "选修课时段限制")
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 检查记录是否使用了选修课时段
        record_periods = set(record.periods)
        elective_used = record_periods & set(self.ELECTIVE_PERIODS)
        
        if not elective_used:
            return result  # 没有使用选修课时段，跳过
        
        # 获取班级年级
        cls = data.get_class(record.class_id)
        if not cls:
            return result
        
        grade = cls.grade
        
        # 检查是否为允许的情况：G8/G9年级 + 周四
        if record.day == self.ELECTIVE_DAY and grade in self.ELECTIVE_GRADES:
            return result  # 允许
        
        # 其他情况不允许
        violation = self.create_violation(
            f"第{list(elective_used)[0]}节为选修课时段，"
            f"只有G8/G9年级周四可用于正课排课（当前: {grade}年级 周{record.day}）",
            severity=ViolationSeverity.CRITICAL,
            class_id=record.class_id,
            grade=grade,
            day=record.day,
            periods=list(elective_used)
        )
        result.add_violation(violation)
        
        return result


class DailySubjectLimitConstraint(HardConstraint):
    """
    每日同科目上限约束
    
    每个班级每天同一科目最多不超过2节课。
    这是一个重要的硬约束，防止某科目在一天内过度集中。
    """
    
    MAX_SAME_SUBJECT_PER_DAY = 2
    
    def __init__(self, max_periods: int = 2):
        super().__init__("HARD_010", "每日同科目上限")
        self.MAX_SAME_SUBJECT_PER_DAY = max_periods
    
    def check(
        self,
        record: 'ScheduleRecord',
        existing_records: List['ScheduleRecord'],
        data: 'ScheduleData'
    ) -> ConstraintCheckResult:
        result = ConstraintCheckResult()
        
        # 统计该班级当天已安排的同科目节数
        same_subject_periods = 0
        
        for existing in existing_records:
            if (existing.class_id == record.class_id and
                existing.day == record.day and
                existing.subject_id == record.subject_id):
                # 累加已安排的节数
                same_subject_periods += existing.duration
        
        # 加上当前记录的节数
        total_periods = same_subject_periods + record.duration
        
        if total_periods > self.MAX_SAME_SUBJECT_PER_DAY:
            subject = data.get_subject(record.subject_id)
            subject_name = subject.name if subject else f"科目{record.subject_id}"
            cls = data.get_class(record.class_id)
            class_name = cls.name if cls else f"班级{record.class_id}"
            
            violation = self.create_violation(
                f"{class_name}周{record.day}的{subject_name}已有{same_subject_periods}节，"
                f"再加{record.duration}节将超过每日上限{self.MAX_SAME_SUBJECT_PER_DAY}节",
                severity=ViolationSeverity.CRITICAL,
                class_id=record.class_id,
                subject_id=record.subject_id,
                day=record.day,
                current_count=same_subject_periods,
                requested=record.duration,
                max_allowed=self.MAX_SAME_SUBJECT_PER_DAY
            )
            result.add_violation(violation)
        
        return result


def create_default_hard_constraints(venue_capacities: Dict[str, int] = None) -> List[HardConstraint]:
    """
    创建默认的硬约束列表
    
    Args:
        venue_capacities: 场地容量配置
    
    Returns:
        List[HardConstraint]: 硬约束列表
    """
    venue_constraint = VenueCapacityConstraint(venue_capacities)
    
    return [
        TeacherConflictConstraint(),
        ClassConflictConstraint(),
        TeacherAvailabilityConstraint(),
        ContinuousBreakConstraint(),
        venue_constraint,
        LayerSyncConstraint(),
        PeriodBoundaryConstraint(),
        FirstPeriodConstraint(),
        ElectivePeriodConstraint(),  # 新增: 选修课时段约束
        DailySubjectLimitConstraint(),  # 新增: 每日同科目上限约束
    ]
