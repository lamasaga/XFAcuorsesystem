from typing import Dict, Set, Tuple, List, Optional
from dataclasses import dataclass, field

# 时间槽类型: (星期几 1-5, 第几节 1-9)
TimeSlot = Tuple[int, int]


@dataclass
class ScheduleRecord:
    """
    单条排课记录
    
    记录一节课的完整信息，用于最后保存到数据库。
    """
    task_id: int          # 教学任务 ID
    teacher_id: int       # 教师 ID
    class_id: int         # 班级 ID
    subject_id: int       # 科目 ID
    day: int              # 星期几 (1-5)
    period: int           # 第几节 (1-9)
    duration: int = 1     # 持续节数（连堂课 > 1）
    layer_group_id: Optional[int] = None  # 分层组ID
    
    # 冗余信息，方便显示
    teacher_name: str = ""
    class_name: str = ""
    subject_name: str = ""
    
    @property
    def periods(self) -> List[int]:
        """返回占用的所有节次"""
        return list(range(self.period, self.period + self.duration))


class ScheduleState:
    """
    排课状态管理类
    
    在内存中维护当前的排课状态，提供快速的查询接口。
    用于在排课算法运行时检查冲突，并记录排课结果。
    """
    def __init__(self):
        # 教师时间表: teacher_id -> set of (day, period)
        # 记录每个教师哪些时间已经被占用
        self.teacher_assignments: Dict[int, Set[TimeSlot]] = {}
        
        # 班级时间表: class_id -> set of (day, period)
        # 记录每个班级哪些时间已经被占用
        self.class_assignments: Dict[int, Set[TimeSlot]] = {}
        
        # 场地使用情况: venue_type -> dict of (day, period) -> count
        # 记录每种场地类型（如'体育'）在每个时间段使用了多少次
        self.venue_usage: Dict[str, Dict[TimeSlot, int]] = {}
        
        # 场地容量限制: venue_type -> max_capacity
        self.venue_capacities: Dict[str, int] = {}
        
        # ========== 新增：排课结果记录 ==========
        # 所有排课记录列表
        self.schedule_records: List[ScheduleRecord] = []
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,      # 总任务数
            "scheduled_tasks": 0,  # 已排课任务数
            "failed_tasks": 0,     # 未能排课的任务数
            "total_periods": 0,    # 总排课节数
        }

    def init_teacher(self, teacher_id: int):
        if teacher_id not in self.teacher_assignments:
            self.teacher_assignments[teacher_id] = set()

    def init_class(self, class_id: int):
        if class_id not in self.class_assignments:
            self.class_assignments[class_id] = set()

    def set_venue_capacity(self, venue_type: str, capacity: int):
        self.venue_capacities[venue_type] = capacity
        if venue_type not in self.venue_usage:
            self.venue_usage[venue_type] = {}

    def is_teacher_busy(self, teacher_id: int, day: int, period: int) -> bool:
        """检查教师是否忙碌"""
        if teacher_id not in self.teacher_assignments:
            return False
        return (day, period) in self.teacher_assignments[teacher_id]

    def is_class_busy(self, class_id: int, day: int, period: int) -> bool:
        """检查班级是否忙碌"""
        if class_id not in self.class_assignments:
            return False
        return (day, period) in self.class_assignments[class_id]

    def check_venue_availability(self, venue_type: str, day: int, period: int) -> bool:
        """检查场地是否有剩余容量"""
        if venue_type not in self.venue_capacities:
            return True # 如果没有配置该场地的限制，默认可用
            
        current_usage = self.venue_usage.get(venue_type, {}).get((day, period), 0)
        return current_usage < self.venue_capacities[venue_type]

    def assign(self, teacher_ids: List[int], class_ids: List[int], day: int, period: int, venue_type: Optional[str] = None):
        """
        占用资源（安排一节课）
        """
        # 占用教师
        for tid in teacher_ids:
            self.init_teacher(tid)
            self.teacher_assignments[tid].add((day, period))
            
        # 占用班级
        for cid in class_ids:
            self.init_class(cid)
            self.class_assignments[cid].add((day, period))
            
        # 占用场地
        if venue_type:
            if venue_type not in self.venue_usage:
                self.venue_usage[venue_type] = {}
            current = self.venue_usage[venue_type].get((day, period), 0)
            self.venue_usage[venue_type][(day, period)] = current + 1

    def unassign(self, teacher_ids: List[int], class_ids: List[int], day: int, period: int, venue_type: Optional[str] = None):
        """
        释放资源（回溯时使用）
        """
        for tid in teacher_ids:
            if tid in self.teacher_assignments:
                self.teacher_assignments[tid].discard((day, period))
                
        for cid in class_ids:
            if cid in self.class_assignments:
                self.class_assignments[cid].discard((day, period))
                
        if venue_type and venue_type in self.venue_usage:
            if (day, period) in self.venue_usage[venue_type]:
                self.venue_usage[venue_type][(day, period)] -= 1
                if self.venue_usage[venue_type][(day, period)] <= 0:
                    del self.venue_usage[venue_type][(day, period)]

    def add_schedule_record(
        self, 
        task_id: int, 
        teacher_id: int, 
        class_id: int, 
        subject_id: int,
        day: int, 
        period: int,
        duration: int = 1,
        layer_group_id: Optional[int] = None,
        teacher_name: str = "",
        class_name: str = "",
        subject_name: str = ""
    ):
        """
        添加一条排课记录
        
        Args:
            task_id: 教学任务 ID
            teacher_id: 教师 ID
            class_id: 班级 ID
            subject_id: 科目 ID
            day: 星期几 (1-5)
            period: 第几节 (1-9)
            duration: 持续节数 (连堂课 > 1)
            layer_group_id: 分层组ID (可选)
            teacher_name: 教师姓名 (可选，用于显示)
            class_name: 班级名称 (可选，用于显示)
            subject_name: 科目名称 (可选，用于显示)
        """
        record = ScheduleRecord(
            task_id=task_id,
            teacher_id=teacher_id,
            class_id=class_id,
            subject_id=subject_id,
            day=day,
            period=period,
            duration=duration,
            layer_group_id=layer_group_id,
            teacher_name=teacher_name,
            class_name=class_name,
            subject_name=subject_name
        )
        self.schedule_records.append(record)
        self.stats["total_periods"] += duration

    def get_all_records(self) -> List[ScheduleRecord]:
        """
        获取所有排课记录
        
        Returns:
            List[ScheduleRecord]: 所有排课记录
        """
        return self.schedule_records.copy()
    
    def get_records_by_teacher(self, teacher_id: int) -> List[ScheduleRecord]:
        """获取某教师的所有排课记录"""
        return [r for r in self.schedule_records if r.teacher_id == teacher_id]
    
    def get_records_by_class(self, class_id: int) -> List[ScheduleRecord]:
        """获取某班级的所有排课记录"""
        return [r for r in self.schedule_records if r.class_id == class_id]
    
    def get_records_by_day(self, day: int) -> List[ScheduleRecord]:
        """获取某天的所有排课记录"""
        return [r for r in self.schedule_records if r.day == day]
    
    def remove_record(self, task_id: int, day: int, period: int) -> bool:
        """
        移除一条排课记录
        
        Args:
            task_id: 任务ID
            day: 星期几
            period: 第几节
            
        Returns:
            bool: 是否成功移除
        """
        for i, record in enumerate(self.schedule_records):
            if record.task_id == task_id and record.day == day and record.period == period:
                del self.schedule_records[i]
                self.stats["total_periods"] -= 1
                return True
        return False
    
    def clear_records(self):
        """清空所有排课记录"""
        self.schedule_records.clear()
        self.teacher_assignments.clear()
        self.class_assignments.clear()
        self.venue_usage.clear()
        self.stats = {
            "total_tasks": 0,
            "scheduled_tasks": 0,
            "failed_tasks": 0,
            "total_periods": 0,
        }

    def get_schedule_summary(self) -> dict:
        """
        获取排课摘要统计
        
        Returns:
            包含统计信息的字典
        """
        # 计算教师空窗期（教师一天内有课的时段之间的空闲节数）
        teacher_gaps = 0
        for teacher_id, slots in self.teacher_assignments.items():
            # 按天分组
            days_dict: Dict[int, List[int]] = {}
            for day, period in slots:
                if day not in days_dict:
                    days_dict[day] = []
                days_dict[day].append(period)
            
            # 计算每天的空窗期
            for day, periods in days_dict.items():
                if len(periods) > 1:
                    sorted_periods = sorted(periods)
                    for i in range(1, len(sorted_periods)):
                        gap = sorted_periods[i] - sorted_periods[i-1] - 1
                        if gap > 0:
                            teacher_gaps += gap
        
        return {
            "total_tasks": self.stats["total_tasks"],
            "scheduled_tasks": self.stats["scheduled_tasks"],
            "failed_tasks": self.stats["failed_tasks"],
            "total_periods": len(self.schedule_records),
            "teacher_gaps": teacher_gaps,
            "records_count": len(self.schedule_records)
        }
