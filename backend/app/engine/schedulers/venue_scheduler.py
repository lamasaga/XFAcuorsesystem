"""
场地课调度器 (The 'Pebble' Scheduler)

负责安排需要特殊场地的课程（如体育、美术、音乐）。
这些课程受场地容量限制，需要在分层课之后、普通课之前排课。

场地约束示例：
- 体育课：体育场同时最多4个班
- 美术课：美术教室同时最多2个班
- 音乐课：音乐教室同时最多2个班
"""

from typing import List, Dict, Set, Tuple, TYPE_CHECKING
from collections import defaultdict
from .base import BaseScheduler

if TYPE_CHECKING:
    from ..data.models import ScheduleData, Task, Venue
    from ..utils.slot_finder import SlotFinder


class VenueScheduler(BaseScheduler):
    """
    场地课调度器
    
    负责安排需要特殊场地的课程。按场地容量限制排序，
    容量越小的越难排，越优先处理。
    
    策略：
    1. 按场地容量限制严格度排序（容量小的优先）
    2. 为每个场地受限任务找到可用时间
    3. 检查场地容量不超限
    4. 支持美术连堂课特殊处理
    
    Usage:
        scheduler = VenueScheduler(state, slot_finder, data)
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
        初始化场地课调度器
        
        Args:
            state: 课表状态管理器
            slot_finder: 时间槽查找器
            data: 排课数据
            db: 数据库会话（可选）
        """
        super().__init__(state, db)
        self.slot_finder = slot_finder
        self.data = data
        
        # 场地容量映射：venue_type -> capacity
        self.venue_capacities: Dict[str, int] = {}
        self._init_venue_capacities()
    
    def _init_venue_capacities(self):
        """初始化场地容量配置"""
        for venue in self.data.venues:
            for subject in venue.subjects:
                # 累加同类型场地的容量
                if subject not in self.venue_capacities:
                    self.venue_capacities[subject] = 0
                self.venue_capacities[subject] += venue.capacity
        
        # 同步到状态管理器
        for venue_type, capacity in self.venue_capacities.items():
            self.state.set_venue_capacity(venue_type, capacity)
    
    def schedule(self) -> List[int]:
        """
        执行场地课排课
        
        Returns:
            List[int]: 成功排课的任务ID列表
        """
        print(">>> 开始场地课排课 (Venue Scheduler)")
        
        # 获取所有需要场地的任务（排除已被分层调度器处理的）
        venue_tasks = self._get_venue_limited_tasks()
        
        if not venue_tasks:
            print("    没有需要场地的任务")
            return []
        
        print(f"    找到 {len(venue_tasks)} 个需要场地的任务")
        
        # 按场地类型分组
        tasks_by_venue = self._group_tasks_by_venue(venue_tasks)
        
        # 按容量限制排序（容量小的优先）
        sorted_venue_types = sorted(
            tasks_by_venue.keys(),
            key=lambda v: self.venue_capacities.get(v, 999)
        )
        
        scheduled_task_ids = []
        
        for venue_type in sorted_venue_types:
            tasks = tasks_by_venue[venue_type]
            capacity = self.venue_capacities.get(venue_type, 1)
            
            print(f"    处理 {venue_type} (容量: {capacity}): {len(tasks)} 个任务")
            
            success_ids = self._schedule_venue_tasks(tasks, venue_type, capacity)
            scheduled_task_ids.extend(success_ids)
        
        print(f"    场地课排课完成，成功 {len(scheduled_task_ids)} 个任务")
        return scheduled_task_ids
    
    def _get_venue_limited_tasks(self) -> List['Task']:
        """获取所有需要场地的任务（排除分层课）"""
        tasks = []
        for task in self.data.tasks:
            # 跳过分层课（已被LayerScheduler处理）
            if task.layer_group_id:
                continue
            
            # 只处理需要场地的任务
            if task.required_venue_type:
                tasks.append(task)
        
        return tasks
    
    def _group_tasks_by_venue(self, tasks: List['Task']) -> Dict[str, List['Task']]:
        """按场地类型分组任务"""
        groups = defaultdict(list)
        for task in tasks:
            if task.required_venue_type:
                groups[task.required_venue_type].append(task)
        return groups
    
    def _schedule_venue_tasks(
        self,
        tasks: List['Task'],
        venue_type: str,
        capacity: int
    ) -> List[int]:
        """
        为一组同类型场地的任务排课
        
        Args:
            tasks: 任务列表
            venue_type: 场地类型
            capacity: 场地容量
        
        Returns:
            List[int]: 成功排课的任务ID列表
        """
        scheduled_ids = []
        
        # 按班级分组任务（同一班级的任务要分散）
        tasks_by_class = defaultdict(list)
        for task in tasks:
            tasks_by_class[task.class_id].append(task)
        
        # 轮流为每个班级排课，尽量分散
        all_scheduled = set()
        
        while True:
            progress = False
            
            for class_id, class_tasks in tasks_by_class.items():
                for task in class_tasks:
                    if task.id in all_scheduled:
                        continue
                    
                    success = self._schedule_single_task(task, venue_type)
                    
                    if success:
                        scheduled_ids.append(task.id)
                        all_scheduled.add(task.id)
                        self.state.stats["scheduled_tasks"] += 1
                        progress = True
                        break  # 这个班级排了一个，换下一个班级
                    else:
                        self.state.stats["failed_tasks"] += 1
            
            # 如果一轮下来没有任何进展，退出
            if not progress:
                break
            
            # 检查是否全部完成
            if len(all_scheduled) == len(tasks):
                break
        
        return scheduled_ids
    
    def _schedule_single_task(self, task: 'Task', venue_type: str) -> bool:
        """
        为单个任务排课
        
        Args:
            task: 任务对象
            venue_type: 场地类型
        
        Returns:
            bool: 是否成功
        """
        # 计算需要排几次课
        sessions_needed = task.sessions_count
        duration = task.session_duration
        
        success_count = 0
        
        for session_idx in range(sessions_needed):
            # 查找可用时间槽
            available_slots = self.slot_finder.find_available_slots(
                teacher_ids=[task.teacher_id],
                class_ids=[task.class_id],
                duration=duration,
                venue_type=venue_type,
                task=task
            )
            
            if not available_slots:
                print(f"      [失败] {task.class_name} 的 {task.subject_name} 第{session_idx + 1}次课找不到时间")
                return False
            
            # 选择第一个可用的时间槽
            day, period = available_slots[0]
            
            # 锁定资源并记录
            self._assign_task_session(task, day, period, duration, venue_type)
            
            success_count += 1
        
        if success_count == sessions_needed:
            print(f"      -> {task.class_name} 的 {task.subject_name}: {sessions_needed}次课排课成功")
            return True
        
        return False
    
    def _assign_task_session(
        self,
        task: 'Task',
        day: int,
        period: int,
        duration: int,
        venue_type: str
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
                venue_type=venue_type
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
    
    def get_venue_usage_summary(self) -> Dict:
        """
        获取场地使用情况摘要
        
        Returns:
            Dict: 场地使用统计
        """
        summary = {
            "venue_capacities": self.venue_capacities.copy(),
            "usage_by_slot": {}
        }
        
        for venue_type in self.venue_capacities:
            usage = self.state.venue_usage.get(venue_type, {})
            summary["usage_by_slot"][venue_type] = {
                "max_concurrent": max(usage.values()) if usage else 0,
                "total_slots_used": len(usage)
            }
        
        return summary
