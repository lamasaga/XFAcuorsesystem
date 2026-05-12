"""
普通课调度器 (The 'Sand' Scheduler)

负责安排剩余的普通课程（非分层、非场地限制）。
这些课程灵活性最高，用于填充剩余空隙。

就像往罐子里倒沙子，填满大石头和鹅卵石之间的空隙。
"""

from typing import List, Dict, Set, Tuple, Optional, TYPE_CHECKING
from collections import defaultdict
from .base import BaseScheduler

if TYPE_CHECKING:
    from ..data.models import ScheduleData, Task
    from ..utils.slot_finder import SlotFinder, SearchStrategy


class NormalScheduler(BaseScheduler):
    """
    普通课调度器
    
    负责安排剩余的普通课程。使用贪心策略，按优先级排序后逐个处理。
    
    策略：
    1. 按优先级排序任务（主科连堂优先）
    2. 为每个任务找到最优时间
    3. 支持连堂课处理
    4. 如果失败，尝试简单回溯
    
    Usage:
        scheduler = NormalScheduler(state, slot_finder, data)
        result = scheduler.schedule()
    """
    
    def __init__(
        self,
        state,
        slot_finder: 'SlotFinder',
        data: 'ScheduleData',
        db=None  # 保持向后兼容
    ):
        """
        初始化普通课调度器
        
        Args:
            state: 课表状态管理器
            slot_finder: 时间槽查找器
            data: 排课数据
            db: 数据库会话（可选）
        """
        super().__init__(state, db)
        self.slot_finder = slot_finder
        self.data = data
        
        # 已排课的任务追踪
        self.scheduled_tasks: Set[int] = set()
        self.failed_tasks: Set[int] = set()
    
    def schedule(self) -> List[int]:
        """
        执行普通课排课
        
        Returns:
            List[int]: 成功排课的任务ID列表
        """
        print(">>> 开始普通课排课 (Normal Scheduler)")
        
        # 获取所有普通任务（排除分层课和场地受限课）
        normal_tasks = self._get_normal_tasks()
        
        if not normal_tasks:
            print("    没有普通任务需要排课")
            return []
        
        print(f"    找到 {len(normal_tasks)} 个普通教学任务")
        
        # 按优先级排序
        sorted_tasks = self._sort_tasks_by_priority(normal_tasks)
        
        # 逐个任务排课
        scheduled_task_ids = []
        
        for task in sorted_tasks:
            success = self._schedule_task(task)
            
            if success:
                scheduled_task_ids.append(task.id)
                self.scheduled_tasks.add(task.id)
                self.state.stats["scheduled_tasks"] += 1
            else:
                self.failed_tasks.add(task.id)
                self.state.stats["failed_tasks"] += 1
        
        self._print_summary(scheduled_task_ids)
        return scheduled_task_ids
    
    def _get_normal_tasks(self) -> List['Task']:
        """获取所有普通任务（非分层、非场地限制）"""
        tasks = []
        for task in self.data.tasks:
            # 跳过分层课
            if task.layer_group_id:
                continue
            
            # 跳过场地受限课（由VenueScheduler处理）
            if task.required_venue_type:
                continue
            
            tasks.append(task)
        
        return tasks
    
    def _sort_tasks_by_priority(self, tasks: List['Task']) -> List['Task']:
        """
        按优先级排序任务
        
        排序规则：
        1. 主科优先
        2. 连堂课优先
        3. 周课时多的优先
        """
        def task_priority(task: 'Task') -> tuple:
            subject = self.data.get_subject(task.subject_id)
            is_main = subject.is_main if subject else False
            
            return (
                -1 if is_main else 0,           # 主科优先
                -1 if task.is_continuous else 0, # 连堂优先
                -task.weekly_hours,              # 周课时多的优先
                task.id                          # ID作为稳定排序
            )
        
        return sorted(tasks, key=task_priority)
    
    def _schedule_task(self, task: 'Task') -> bool:
        """
        为单个任务排课
        
        Args:
            task: 任务对象
        
        Returns:
            bool: 是否完全成功
        """
        # 计算需要排几次课
        sessions_needed = task.sessions_count
        duration = task.session_duration
        
        scheduled_sessions = 0
        
        for session_idx in range(sessions_needed):
            success = self._schedule_single_session(task, duration, session_idx + 1, sessions_needed)
            if success:
                scheduled_sessions += 1
            else:
                # 尝试非连堂方式
                if duration > 1:
                    # 如果连堂失败，尝试拆分为单节
                    print(f"      连堂失败，尝试拆分排课...")
                    for _ in range(duration):
                        if self._schedule_single_session(task, 1, session_idx + 1, sessions_needed):
                            scheduled_sessions += 1
        
        # 计算实际排了多少课时
        actual_hours = scheduled_sessions * duration if duration > 1 else scheduled_sessions
        
        if actual_hours >= task.weekly_hours:
            return True
        elif actual_hours > 0:
            # 部分成功
            print(f"    [部分成功] {task.class_name} {task.subject_name}: {actual_hours}/{task.weekly_hours} 课时")
            return True
        else:
            print(f"    [失败] {task.class_name} {task.subject_name}: 无法排课")
            return False
    
    def _schedule_single_session(
        self,
        task: 'Task',
        duration: int,
        current: int,
        total: int
    ) -> bool:
        """
        安排一次课
        
        Args:
            task: 任务对象
            duration: 持续节数
            current: 当前是第几次
            total: 共需要排几次
        
        Returns:
            bool: 是否成功
        """
        # 根据科目特性选择搜索策略
        from ..utils.slot_finder import SearchStrategy
        
        subject = self.data.get_subject(task.subject_id)
        if subject and subject.is_main:
            strategy = SearchStrategy.MORNING_FIRST
        else:
            strategy = SearchStrategy.FIRST_FIT
        
        # 查找可用时间槽
        available_slots = self.slot_finder.find_available_slots(
            teacher_ids=[task.teacher_id],
            class_ids=[task.class_id],
            duration=duration,
            venue_type=None,
            strategy=strategy,
            task=task,
            limit=1
        )
        
        if not available_slots:
            return False
        
        day, period = available_slots[0]
        
        # 锁定资源并记录
        self._assign_task_session(task, day, period, duration)
        
        return True
    
    def _assign_task_session(
        self,
        task: 'Task',
        day: int,
        period: int,
        duration: int
    ):
        """安排一次课"""
        for i in range(duration):
            current_period = period + i
            
            # 锁定状态
            self.state.assign(
                teacher_ids=[task.teacher_id],
                class_ids=[task.class_id],
                day=day,
                period=current_period,
                venue_type=None
            )
            
            # 添加排课记录
            self.state.add_schedule_record(
                task_id=task.id,
                teacher_id=task.teacher_id,
                class_id=task.class_id,
                subject_id=task.subject_id,
                day=day,
                period=current_period,
                teacher_name=task.teacher_name,
                class_name=task.class_name,
                subject_name=task.subject_name
            )
    
    def _print_summary(self, scheduled_ids: List[int]):
        """打印排课摘要"""
        total_tasks = len(self.scheduled_tasks) + len(self.failed_tasks)
        success_rate = len(self.scheduled_tasks) / total_tasks * 100 if total_tasks > 0 else 0
        
        print(f"    普通课排课完成:")
        print(f"      - 成功: {len(self.scheduled_tasks)} 个任务")
        print(f"      - 失败: {len(self.failed_tasks)} 个任务")
        print(f"      - 成功率: {success_rate:.1f}%")
        print(f"      - 总课时: {self.state.stats['total_periods']} 节")
    
    def get_failed_tasks(self) -> List['Task']:
        """获取排课失败的任务列表"""
        return [self.data.get_task(tid) for tid in self.failed_tasks if self.data.get_task(tid)]
