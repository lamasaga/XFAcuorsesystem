"""
时间槽查找器

负责在时间表中寻找符合所有约束的空闲时间槽。
它是排课引擎的"眼睛"。

重构说明：
1. 支持约束注入，可以自定义检查逻辑
2. 使用新的数据模型，与ORM解耦
3. 提供更灵活的搜索策略
"""

from typing import List, Tuple, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from ..state import ScheduleState
    from ..data.models import ScheduleData, Task, ScheduleRecord
    from ..constraints import ConstraintChecker


# 时间槽类型定义
TimeSlot = Tuple[int, int]  # (day, period)


class SearchStrategy(Enum):
    """搜索策略"""
    FIRST_FIT = "first_fit"      # 找到第一个可用的就返回
    BEST_FIT = "best_fit"        # 评估所有可用槽，选最优的
    RANDOM = "random"            # 随机选择一个可用的
    MORNING_FIRST = "morning"    # 优先上午
    AFTERNOON_FIRST = "afternoon"  # 优先下午


@dataclass
class SlotSearchConfig:
    """
    时间槽搜索配置
    
    Attributes:
        days: 搜索的天数范围 (默认1-5)
        morning_periods: 上午节次 [1,2,3,4,5]
        afternoon_periods: 下午节次 [6,7,8,9]
        regular_max_period: 常规最大节次（不含选修课）
        friday_max_period: 周五最大节次
        lunch_break_after: 午休在第几节之后
        
        # 第10-11节选修课特殊规则
        elective_periods: 选修课节次 [10, 11]
        elective_day: 选修课可用于正课的星期（周四=4）
        elective_grades: 可使用选修课节次上正课的年级 ['G8', 'G9']
    """
    days: List[int] = None
    morning_periods: List[int] = None
    afternoon_periods: List[int] = None
    regular_max_period: int = 9  # 常规9节课
    friday_max_period: int = 8   # 周五8节课
    lunch_break_after: int = 5
    
    # 第10-11节选修课特殊规则
    elective_periods: List[int] = None  # [10, 11]
    elective_day: int = 4  # 周四
    elective_grades: List[str] = None  # ['G8', 'G9']
    
    def __post_init__(self):
        if self.days is None:
            self.days = [1, 2, 3, 4, 5]
        if self.morning_periods is None:
            self.morning_periods = [1, 2, 3, 4, 5]
        if self.afternoon_periods is None:
            self.afternoon_periods = [6, 7, 8, 9]
        if self.elective_periods is None:
            self.elective_periods = [10, 11]
        if self.elective_grades is None:
            self.elective_grades = ['G8', 'G9']
    
    def get_max_period_for_grade(self, day: int, grade: str) -> int:
        """
        获取特定年级在特定日期的最大可用节次
        
        Args:
            day: 星期几 (1-5)
            grade: 年级代码 (如 'G8', 'G9')
        
        Returns:
            int: 最大可用节次
        """
        # 周五固定8节
        if day == 5:
            return self.friday_max_period
        
        # G8/G9年级周四可用到第11节
        if day == self.elective_day and grade in self.elective_grades:
            return max(self.elective_periods)  # 11
        
        # 其他情况使用常规最大节次
        return self.regular_max_period
    
    def is_elective_slot(self, day: int, period: int, grade: str) -> bool:
        """
        判断某个时间槽是否为选修课时段（不可用于正课排课）
        
        Args:
            day: 星期几
            period: 第几节
            grade: 年级代码
        
        Returns:
            bool: True表示是选修课时段，不能排正课
        """
        if period not in self.elective_periods:
            return False
        
        # G8/G9年级周四的10-11节可以排正课
        if day == self.elective_day and grade in self.elective_grades:
            return False
        
        # 其他情况下10-11节为选修课时段
        return True


class SlotFinder:
    """
    时间槽查找器
    
    负责在时间表中寻找符合所有硬约束的空闲时间槽。
    
    Usage:
        # 基本用法
        finder = SlotFinder(state, data)
        slots = finder.find_available_slots(
            teacher_ids=[1, 2],
            class_ids=[10, 11],
            duration=2
        )
        
        # 使用约束检查器
        finder = SlotFinder(state, data, constraint_checker=checker)
        slots = finder.find_available_slots(...)
    """
    
    def __init__(
        self,
        state: 'ScheduleState',
        data: 'ScheduleData' = None,
        constraint_checker: 'ConstraintChecker' = None,
        config: SlotSearchConfig = None
    ):
        """
        初始化时间槽查找器
        
        Args:
            state: 课表状态管理器
            data: 排课数据（用于约束检查）
            constraint_checker: 约束检查器（可选）
            config: 搜索配置
        """
        self.state = state
        self.data = data
        self.constraint_checker = constraint_checker
        self.config = config or SlotSearchConfig()
    
    def find_available_slots(
        self,
        teacher_ids: List[int],
        class_ids: List[int],
        duration: int = 1,
        venue_type: Optional[str] = None,
        strategy: SearchStrategy = SearchStrategy.FIRST_FIT,
        task: 'Task' = None,
        limit: int = None,
        grade: str = None
    ) -> List[TimeSlot]:
        """
        查找可用时间槽
        
        Args:
            teacher_ids: 涉及的教师ID列表
            class_ids: 涉及的班级ID列表
            duration: 持续节数 (默认1)
            venue_type: 需要的场地类型
            strategy: 搜索策略
            task: 任务对象（用于软约束评分）
            limit: 最多返回多少个结果
            grade: 年级代码（用于判断选修课时段）
            
        Returns:
            List[TimeSlot]: 可用的起始时间槽列表，按策略排序
        """
        valid_slots = []
        
        # 从任务中获取年级（如果未指定）
        if grade is None and task and self.data:
            cls = self.data.get_class(task.class_id)
            if cls:
                grade = cls.grade
        
        # 生成搜索空间（考虑年级和选修课时段）
        search_space = self._generate_search_space(strategy, grade)
        
        for day, period in search_space:
            # 检查连堂课的边界条件
            if not self._is_valid_duration(day, period, duration, grade):
                continue
            
            # 检查是否为选修课时段（不可排正课）
            if grade and self.config.is_elective_slot(day, period, grade):
                continue
            
            # 检查所有时间槽是否可用
            if self._check_all_slots(teacher_ids, class_ids, venue_type, day, period, duration, task, grade):
                valid_slots.append((day, period))
                
                # FIRST_FIT 策略找到一个就返回
                if strategy == SearchStrategy.FIRST_FIT:
                    return valid_slots
                
                # 达到限制就返回
                if limit and len(valid_slots) >= limit:
                    break
        
        # BEST_FIT 策略需要评分排序
        if strategy == SearchStrategy.BEST_FIT and task and self.constraint_checker:
            valid_slots = self._sort_by_score(valid_slots, teacher_ids, class_ids, task, duration)
        
        return valid_slots
    
    def find_first_available(
        self,
        teacher_ids: List[int],
        class_ids: List[int],
        duration: int = 1,
        venue_type: Optional[str] = None,
        task: 'Task' = None
    ) -> Optional[TimeSlot]:
        """
        查找第一个可用时间槽（便捷方法）
        
        Returns:
            Optional[TimeSlot]: 第一个可用的时间槽，或None
        """
        slots = self.find_available_slots(
            teacher_ids=teacher_ids,
            class_ids=class_ids,
            duration=duration,
            venue_type=venue_type,
            strategy=SearchStrategy.FIRST_FIT,
            task=task
        )
        return slots[0] if slots else None
    
    def find_best_slot(
        self,
        teacher_ids: List[int],
        class_ids: List[int],
        duration: int = 1,
        venue_type: Optional[str] = None,
        task: 'Task' = None
    ) -> Optional[TimeSlot]:
        """
        查找最优时间槽（根据软约束评分）
        
        Returns:
            Optional[TimeSlot]: 最优的时间槽，或None
        """
        slots = self.find_available_slots(
            teacher_ids=teacher_ids,
            class_ids=class_ids,
            duration=duration,
            venue_type=venue_type,
            strategy=SearchStrategy.BEST_FIT,
            task=task
        )
        return slots[0] if slots else None
    
    def is_slot_available(
        self,
        teacher_ids: List[int],
        class_ids: List[int],
        day: int,
        period: int,
        duration: int = 1,
        venue_type: Optional[str] = None,
        task: 'Task' = None
    ) -> bool:
        """
        检查特定时间槽是否可用
        
        Args:
            teacher_ids: 教师ID列表
            class_ids: 班级ID列表
            day: 星期几
            period: 第几节
            duration: 持续节数
            venue_type: 场地类型
            task: 任务对象
        
        Returns:
            bool: 是否可用
        """
        if not self._is_valid_duration(day, period, duration):
            return False
        
        return self._check_all_slots(teacher_ids, class_ids, venue_type, day, period, duration, task)
    
    def _generate_search_space(self, strategy: SearchStrategy, grade: str = None) -> List[TimeSlot]:
        """
        生成搜索空间
        
        Args:
            strategy: 搜索策略
            grade: 年级代码（用于判断选修课时段的可用性）
        """
        slots = []
        
        for day in self.config.days:
            # 根据年级和日期确定最大节次
            if grade:
                max_period = self.config.get_max_period_for_grade(day, grade)
            else:
                # 如果没有年级信息，使用保守的常规最大节次
                max_period = self.config.friday_max_period if day == 5 else self.config.regular_max_period
            
            if strategy == SearchStrategy.MORNING_FIRST:
                # 先上午后下午（优先前面的时段）
                periods = self.config.morning_periods + [p for p in self.config.afternoon_periods if p <= max_period]
            elif strategy == SearchStrategy.AFTERNOON_FIRST:
                # 先下午后上午
                periods = [p for p in self.config.afternoon_periods if p <= max_period] + self.config.morning_periods
            else:
                # 默认顺序：优先常规课时，最后考虑选修课时段
                regular_periods = list(range(1, min(max_period + 1, self.config.regular_max_period + 1)))
                # 只有G8/G9年级周四才添加10-11节
                if grade and day == self.config.elective_day and grade in self.config.elective_grades:
                    elective = [p for p in self.config.elective_periods if p <= max_period]
                    periods = regular_periods + elective
                else:
                    periods = regular_periods
            
            for period in periods:
                if period <= max_period:
                    slots.append((day, period))
        
        if strategy == SearchStrategy.RANDOM:
            import random
            random.shuffle(slots)
        
        return slots
    
    def _is_valid_duration(self, day: int, start_period: int, duration: int, grade: str = None) -> bool:
        """检查连堂课是否跨越了非法边界"""
        if duration == 1:
            return True
        
        # 根据年级和日期确定最大节次
        if grade:
            max_period = self.config.get_max_period_for_grade(day, grade)
        else:
            max_period = self.config.friday_max_period if day == 5 else self.config.regular_max_period
        
        end_period = start_period + duration - 1
        
        # 检查是否超出当天的最大节数
        if end_period > max_period:
            return False
        
        # 检查是否跨越午休（第5-6节之间）
        lunch_after = self.config.lunch_break_after
        if start_period <= lunch_after < end_period:
            return False
        
        # 检查是否跨越常规课与选修课的边界（第9-10节之间）
        # 除非是G8/G9年级周四，且是连续2节放在10-11节
        if start_period <= self.config.regular_max_period < end_period:
            # 允许G8/G9年级周四在10-11节放连堂
            if day == self.config.elective_day and grade in self.config.elective_grades:
                # 但必须整个连堂都在10-11节内
                if start_period >= self.config.elective_periods[0]:
                    return True
            return False
        
        return True
    
    def _check_all_slots(
        self,
        teacher_ids: List[int],
        class_ids: List[int],
        venue_type: Optional[str],
        day: int,
        period: int,
        duration: int,
        task: 'Task' = None,
        grade: str = None
    ) -> bool:
        """检查从指定位置开始的所有时间槽是否可用"""
        for i in range(duration):
            current_period = period + i
            
            # 检查每个时间槽是否为选修课时段
            if grade and self.config.is_elective_slot(day, current_period, grade):
                return False
            
            if not self._check_single_slot(teacher_ids, class_ids, venue_type, day, current_period, task):
                return False
        return True
    
    def _check_single_slot(
        self,
        teacher_ids: List[int],
        class_ids: List[int],
        venue_type: Optional[str],
        day: int,
        period: int,
        task: 'Task' = None
    ) -> bool:
        """检查单个时间槽是否可用"""
        
        # 1. 检查教师冲突
        for tid in teacher_ids:
            if self.state.is_teacher_busy(tid, day, period):
                return False
        
        # 2. 检查班级冲突
        for cid in class_ids:
            if self.state.is_class_busy(cid, day, period):
                return False
        
        # 3. 检查场地容量
        if venue_type:
            if not self.state.check_venue_availability(venue_type, day, period):
                return False
        
        # 4. 检查教师可用性（如果有数据）
        if self.data:
            for tid in teacher_ids:
                teacher = self.data.get_teacher(tid)
                if teacher and not teacher.is_available(day, period):
                    return False
        
        return True
    
    def _sort_by_score(
        self,
        slots: List[TimeSlot],
        teacher_ids: List[int],
        class_ids: List[int],
        task: 'Task',
        duration: int
    ) -> List[TimeSlot]:
        """根据软约束评分对时间槽排序"""
        if not self.constraint_checker or not self.data:
            return slots
        
        from ..data.models import ScheduleRecord
        
        scored_slots = []
        existing_records = self.state.get_all_records()
        
        for day, period in slots:
            # 创建临时记录用于评分
            temp_record = ScheduleRecord(
                task_id=task.id,
                teacher_id=task.teacher_id,
                class_id=task.class_id,
                subject_id=task.subject_id,
                day=day,
                period=period,
                duration=duration,
                layer_group_id=task.layer_group_id
            )
            
            # 只评估软约束
            result = self.constraint_checker.check_soft(temp_record, existing_records, self.data)
            scored_slots.append((day, period, result.score))
        
        # 按分数降序排序
        scored_slots.sort(key=lambda x: x[2], reverse=True)
        
        return [(day, period) for day, period, _ in scored_slots]


def create_slot_finder(
    state: 'ScheduleState',
    data: 'ScheduleData' = None,
    use_constraints: bool = True
) -> SlotFinder:
    """
    创建时间槽查找器（便捷函数）
    
    Args:
        state: 课表状态
        data: 排课数据
        use_constraints: 是否使用约束检查器
    
    Returns:
        SlotFinder: 配置好的查找器
    """
    constraint_checker = None
    
    if use_constraints and data:
        from ..constraints import create_default_checker
        
        # 获取场地容量
        venue_capacities = {}
        for venue in data.venues:
            for subject in venue.subjects:
                venue_capacities[subject] = venue_capacities.get(subject, 0) + venue.capacity
        
        constraint_checker = create_default_checker(venue_capacities)
    
    return SlotFinder(
        state=state,
        data=data,
        constraint_checker=constraint_checker
    )
