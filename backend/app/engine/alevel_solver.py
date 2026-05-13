"""
========================================
A-Level 排课求解器（顺序排课模式）
========================================

在行政班排课完成后，为 A-Level 课程班在剩余空闲时段中自动排课。

设计要点：
1. 行政班排课结果作为输入（已占用的 time slots）
2. A-Level 课程优先使用第 10-11 节（选修课时间）
3. 学生不冲突：同一学生同一时刻只能上一门 A-Level 课
4. 教师不冲突：同一教师同一时刻只能教一门 A-Level 课
5. 时段限制：避开行政班主科（语数英）时间

使用方法：
    from app.engine.alevel_solver import AlevelScheduleSolver
    
    solver = AlevelScheduleSolver(data, occupied_slots)
    records = solver.solve()
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from ortools.sat.python import cp_model

from .data.models import (
    ScheduleData, AlevelScheduleSession, DepartmentTimeSlots, ScheduleRecord
)


@dataclass
class AlevelScheduleRecord:
    """A-Level 排课记录"""
    course_class_id: int
    teacher_id: int
    day: int
    period: int
    duration: int = 1
    student_ids: List[int] = field(default_factory=list)
    aleve_subject_id: int = 0

    @property
    def time_slot(self) -> str:
        days = ['', '周一', '周二', '周三', '周四', '周五']
        return f"{days[self.day]}第{self.period}节"

    @property
    def periods(self) -> List[int]:
        return list(range(self.period, self.period + self.duration))

    def to_dict(self) -> dict:
        return {
            "course_class_id": self.course_class_id,
            "teacher_id": self.teacher_id,
            "day": self.day,
            "period": self.period,
            "duration": self.duration,
            "student_ids": self.student_ids,
            "aleve_subject_id": self.aleve_subject_id,
        }


class AlevelScheduleSolver:
    """
    A-Level 排课求解器
    
    基于 OR-Tools CP-SAT，在行政班排课后的剩余时段中为 A-Level 课程排课。
    """

    def __init__(
        self,
        data: ScheduleData,
        teacher_occupied: Optional[Dict[Tuple[int, int, int], bool]] = None,
        student_occupied: Optional[Dict[Tuple[int, int, int], bool]] = None,
        prefer_elective_slots: bool = True,
    ):
        """
        初始化求解器
        
        Args:
            data: 排课数据集（含 alevel_sessions 和 time_slots）
            teacher_occupied: 教师已被行政班占用的时间槽 {(teacher_id, day, period): True}
            student_occupied: 学生已被行政班占用的时间槽 {(student_id, day, period): True}
            prefer_elective_slots: 是否优先使用第 10-11 节选修课时间
        """
        self.data = data
        self.teacher_occupied = teacher_occupied or {}
        self.student_occupied = student_occupied or {}
        self.prefer_elective_slots = prefer_elective_slots
        
        # 获取高中部时间槽配置
        self.senior_slots: Optional[DepartmentTimeSlots] = data.time_slots.get("SENIOR")
        
        # CP-SAT 模型
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # 决策变量: {session_idx: {(day, period): BoolVar}}
        self.x: Dict[int, Dict[Tuple[int, int], cp_model.IntVar]] = {}

    def solve(self) -> List[AlevelScheduleRecord]:
        """
        执行 A-Level 排课求解
        
        Returns:
            List[AlevelScheduleRecord]: 排课结果列表
        """
        sessions = self.data.alevel_sessions
        if not sessions:
            print("[A-Level 排课] 无 A-Level 课程班，跳过")
            return []
        
        print(f"[A-Level 排课] 开始求解，{len(sessions)} 个课程班")
        
        # 1. 构建可用时间槽
        self._build_available_slots(sessions)
        
        # 2. 创建变量
        self._create_variables(sessions)
        
        # 3. 添加约束
        self._add_constraints(sessions)
        
        # 4. 添加目标函数（软约束：优先选修课时段）
        self._add_objective(sessions)
        
        # 5. 求解
        status = self.solver.Solve(self.model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            records = self._extract_solution(sessions)
            print(f"[A-Level 排课] 求解成功，安排 {len(records)} 个课程班")
            return records
        else:
            print(f"[A-Level 排课] 求解失败，状态: {status}")
            return []

    def _build_available_slots(self, sessions: List[AlevelScheduleSession]):
        """
        为每个 session 构建可用时间槽列表
        
        根据高中部时间槽配置和行政班已占用 slots，确定每个 session 可以安排的时间。
        """
        self.session_slots: Dict[int, List[Tuple[int, int]]] = {}
        
        for idx, session in enumerate(sessions):
            slots = []
            for day in range(1, 6):
                # 获取该天的最大节次
                if self.senior_slots:
                    max_period = self.senior_slots.get_max_period(day)
                else:
                    max_period = 8 if day == 5 else 13
                
                for period in range(1, max_period + 1):
                    end_period = period + session.duration - 1
                    if end_period > max_period:
                        continue
                    
                    # 检查教师是否在该时段已有行政班课程
                    teacher_busy = False
                    for p in range(period, end_period + 1):
                        if self.teacher_occupied.get((session.teacher_id, day, p)):
                            teacher_busy = True
                            break
                    if teacher_busy:
                        continue
                    
                    # 检查学生是否在该时段已有行政班课程
                    student_busy = False
                    for p in range(period, end_period + 1):
                        for student_id in session.student_ids:
                            if self.student_occupied.get((student_id, day, p)):
                                student_busy = True
                                break
                        if student_busy:
                            break
                    if student_busy:
                        continue
                    
                    slots.append((day, period))
            
            self.session_slots[idx] = slots

    def _create_variables(self, sessions: List[AlevelScheduleSession]):
        """为每个 session 创建决策变量"""
        for idx, session in enumerate(sessions):
            slot_vars = {}
            for day, period in self.session_slots[idx]:
                var_name = f"alevel_s{idx}_d{day}_p{period}"
                slot_vars[(day, period)] = self.model.NewBoolVar(var_name)
            self.x[idx] = slot_vars

    def _add_constraints(self, sessions: List[AlevelScheduleSession]):
        """添加硬约束"""
        
        # C1: 每个 session 恰好分配一个槽位
        for idx, session in enumerate(sessions):
            vars_list = list(self.x[idx].values())
            if not vars_list:
                print(f"  警告: 课程班 {session.course_class_id} 无可用时间槽")
                continue
            self.model.AddExactlyOne(vars_list)
        
        # C2: 教师不冲突
        teacher_day_period: Dict[Tuple[int, int, int], List[cp_model.IntVar]] = defaultdict(list)
        for idx, session in enumerate(sessions):
            for (day, period), var in self.x[idx].items():
                teacher_day_period[(session.teacher_id, day, period)].append(var)
        
        for key, vars_list in teacher_day_period.items():
            if len(vars_list) > 1:
                self.model.AddAtMostOne(vars_list)
        
        # C3: 学生不冲突
        student_day_period: Dict[Tuple[int, int, int], List[cp_model.IntVar]] = defaultdict(list)
        for idx, session in enumerate(sessions):
            for (day, period), var in self.x[idx].items():
                for student_id in session.student_ids:
                    student_day_period[(student_id, day, period)].append(var)
        
        for key, vars_list in student_day_period.items():
            if len(vars_list) > 1:
                self.model.AddAtMostOne(vars_list)

    def _add_objective(self, sessions: List[AlevelScheduleSession]):
        """添加目标函数：优先选修课时段（第10-11节）"""
        if not self.prefer_elective_slots:
            return
        
        terms = []
        for idx, session in enumerate(sessions):
            for (day, period), var in self.x[idx].items():
                # 优先级评分
                score = 0
                
                # P1: 第 10-11 节（选修课时间，首选）
                if 10 <= period <= 11:
                    score += 100
                # P2: 第 8-9 节（次选）
                elif 8 <= period <= 9:
                    score += 50
                # P3: 第 6-7 节
                elif 6 <= period <= 7:
                    score += 20
                # P4: 第 1-5 节（尽量避免，与行政班重叠）
                else:
                    score += 5
                
                # 周五扣分（周五只有 8 节，且 A-Level 通常不安排在周五）
                if day == 5:
                    score -= 30
                
                if score > 0:
                    terms.append(var * score)
        
        if terms:
            self.model.Maximize(sum(terms))

    def _extract_solution(self, sessions: List[AlevelScheduleSession]) -> List[AlevelScheduleRecord]:
        """从求解结果中提取排课记录"""
        records = []
        for idx, session in enumerate(sessions):
            for (day, period), var in self.x[idx].items():
                if self.solver.Value(var) == 1:
                    records.append(AlevelScheduleRecord(
                        course_class_id=session.course_class_id,
                        teacher_id=session.teacher_id,
                        day=day,
                        period=period,
                        duration=session.duration,
                        student_ids=session.student_ids,
                        aleve_subject_id=session.aleve_subject_id,
                    ))
                    break
        return records
