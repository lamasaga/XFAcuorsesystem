"""
分层课调度器 (The 'Big Rock' Scheduler)

负责安排分层走班课程。
特点：多个班级和多个教师必须在同一时间上课。

分层课是排课中最复杂的约束，必须优先处理。
就像往罐子里装东西，要先放大石头。
"""

from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from .base import BaseScheduler

if TYPE_CHECKING:
    from ..data.models import ScheduleData, Task, LayerGroup, ScheduleRecord
    from ..utils.slot_finder import SlotFinder


class LayerScheduler(BaseScheduler):
    """
    分层课调度器
    
    负责安排分层走班课程。分层课需要多个班级的学生重新分组，
    由不同老师同时上课，因此这些课必须安排在同一时间。
    
    策略：
    1. 按复杂度排序分层组（跨年级、层数多的优先）
    2. 为每个分层组找到所有老师和班级都空闲的时间
    3. 支持连堂课处理
    4. 如果失败，尝试回溯
    
    Usage:
        scheduler = LayerScheduler(state, slot_finder, data)
        result = scheduler.schedule()
    """
    
    def __init__(
        self,
        state,
        slot_finder: 'SlotFinder',
        data: 'ScheduleData',
        db=None,  # 保持向后兼容
        max_backtrack: int = 10
    ):
        """
        初始化分层课调度器
        
        Args:
            state: 课表状态管理器
            slot_finder: 时间槽查找器
            data: 排课数据
            db: 数据库会话（可选，保持向后兼容）
            max_backtrack: 最大回溯次数
        """
        super().__init__(state, db)
        self.slot_finder = slot_finder
        self.data = data
        self.max_backtrack = max_backtrack
        
        # 排课结果
        self.scheduled_sessions: List[Tuple[int, int, int, int]] = []  # [(layer_group_id, day, period, duration)]
    
    def schedule(self) -> List[int]:
        """
        执行分层课排课
        
        Returns:
            List[int]: 成功排课的任务ID列表
        """
        print(">>> 开始分层课排课 (Layer Scheduler)")
        
        # 获取所有分层组，按复杂度排序
        layer_groups = sorted(
            self.data.layer_groups,
            key=lambda g: g.complexity,
            reverse=True  # 复杂度高的优先
        )
        
        print(f"    找到 {len(layer_groups)} 个分层组")
        
        scheduled_task_ids = []
        
        for group in layer_groups:
            success = self._schedule_layer_group(group)
            
            if success:
                # 收集该分层组的所有任务ID
                tasks = self.data.get_layer_tasks(group.id)
                scheduled_task_ids.extend([t.id for t in tasks])
                self.state.stats["scheduled_tasks"] += len(tasks)
            else:
                tasks = self.data.get_layer_tasks(group.id)
                self.state.stats["failed_tasks"] += len(tasks)
        
        print(f"    分层课排课完成，成功 {len(scheduled_task_ids)} 个任务")
        return scheduled_task_ids
    
    def _schedule_layer_group(self, group: 'LayerGroup') -> bool:
        """
        为单个分层组排课
        
        Args:
            group: 分层组对象
        
        Returns:
            bool: 是否完全成功
        """
        group_type_name = "合班" if group.is_combine else "分层"
        if group.is_combine:
            target_info = f"班级IDs={group.class_ids}"
        elif group.is_single_class:
            target_info = f"单班 class_ids={group.class_ids}"
        else:
            target_info = f"年级={group.grades}"
        print(f"    处理{group_type_name}组: ID={group.id}, 科目={group.subject_name}, {target_info}")
        
        # 获取关联的所有任务
        tasks = self.data.get_layer_tasks(group.id)
        
        if not tasks:
            print(f"    [警告] 分层组 {group.id} 没有关联的教学任务，跳过")
            return False
        
        # 收集涉及的所有教师和班级
        teacher_ids = list(set(t.teacher_id for t in tasks))
        class_ids = list(set(t.class_id for t in tasks))
        
        print(f"      涉及 {len(teacher_ids)} 位教师, {len(class_ids)} 个班级")
        
        # 计算需要排几次课
        weekly_hours = group.weekly_hours
        duration = 2 if group.needs_continuous else 1
        sessions_needed = weekly_hours // duration
        
        print(f"      需要排 {sessions_needed} 次课 (每次 {duration} 节)")
        
        # 排课
        success_count = 0
        backtrack_count = 0
        
        for session_idx in range(sessions_needed):
            # 查找可用时间槽
            available_slots = self.slot_finder.find_available_slots(
                teacher_ids=teacher_ids,
                class_ids=class_ids,
                duration=duration,
                venue_type=None,  # 分层课通常在普通教室
                limit=5  # 获取多个候选，用于回溯
            )
            
            if not available_slots:
                print(f"      [失败] 无法为第 {session_idx + 1} 次课找到时间")
                
                # 尝试回溯
                if backtrack_count < self.max_backtrack and success_count > 0:
                    print(f"      尝试回溯...")
                    if self._backtrack_last_session(group.id, teacher_ids, class_ids, duration):
                        backtrack_count += 1
                        session_idx -= 1  # 重试当前session
                        success_count -= 1
                        continue
                
                return False
            
            # 选择第一个可用的时间槽
            day, period = available_slots[0]
            
            # 锁定资源
            self._assign_layer_session(
                group=group,
                tasks=tasks,
                teacher_ids=teacher_ids,
                class_ids=class_ids,
                day=day,
                period=period,
                duration=duration
            )
            
            # 记录已排的session
            self.scheduled_sessions.append((group.id, day, period, duration))
            
            print(f"      -> 第 {session_idx + 1} 次课: 周{day} 第{period}节" + 
                  (f"(连堂{duration}节)" if duration > 1 else ""))
            success_count += 1
        
        return success_count == sessions_needed
    
    def _assign_layer_session(
        self,
        group: 'LayerGroup',
        tasks: List['Task'],
        teacher_ids: List[int],
        class_ids: List[int],
        day: int,
        period: int,
        duration: int
    ):
        """
        安排一次分层课
        
        锁定所有涉及的教师和班级的时间，并记录排课结果。
        """
        # 为连堂课的每个节次都锁定资源
        for i in range(duration):
            current_period = period + i
            
            # 锁定状态
            self.state.assign(
                teacher_ids=teacher_ids,
                class_ids=class_ids,
                day=day,
                period=current_period,
                venue_type=None
            )
            
            # 为每个任务添加排课记录
            for task in tasks:
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
    
    def _backtrack_last_session(
        self,
        group_id: int,
        teacher_ids: List[int],
        class_ids: List[int],
        duration: int
    ) -> bool:
        """
        回溯上一次排课
        
        释放上一次排课占用的资源，以便尝试其他时间。
        
        Returns:
            bool: 是否成功回溯
        """
        # 找到该分层组最后一次排课
        for i in range(len(self.scheduled_sessions) - 1, -1, -1):
            gid, day, period, dur = self.scheduled_sessions[i]
            if gid == group_id:
                # 释放资源
                for j in range(dur):
                    current_period = period + j
                    self.state.unassign(
                        teacher_ids=teacher_ids,
                        class_ids=class_ids,
                        day=day,
                        period=current_period,
                        venue_type=None
                    )
                
                # 移除该分层组所有任务在该时间的记录
                tasks = self.data.get_layer_tasks(group_id)
                for task in tasks:
                    for j in range(dur):
                        self.state.remove_record(task.id, day, period + j)
                
                # 从scheduled_sessions中移除
                del self.scheduled_sessions[i]
                
                return True
        
        return False
    
    def get_layer_schedule_summary(self) -> Dict:
        """
        获取分层课排课摘要
        
        Returns:
            Dict: 摘要信息
        """
        summary = {
            "total_groups": len(self.data.layer_groups),
            "scheduled_sessions": len(self.scheduled_sessions),
            "sessions_by_group": {}
        }
        
        for gid, day, period, duration in self.scheduled_sessions:
            if gid not in summary["sessions_by_group"]:
                summary["sessions_by_group"][gid] = []
            summary["sessions_by_group"][gid].append({
                "day": day,
                "period": period,
                "duration": duration
            })
        
        return summary
