"""
CP-SAT 排课求解器 (v2 - 三层约束体系)

约束分层：
- Tier 1 (物理硬约束): 教师/班级无冲突、分层组同步、场地容量上限
- Tier 2 (严格约束): 同科目每日<=2节
- Tier 3 (软约束): 用户可配置优先级和权重

主要组件：
- ScheduleSession: 统一的排课决策单元
- SessionBuilder: Task/LayerGroup -> Session 转换器
- CPScheduleSolver: CP-SAT 模型构建、求解、结果提取
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
import time

from ortools.sat.python import cp_model

from ..data.models import (
    ScheduleData, Task, LayerGroup, Class, Teacher, Subject, Venue,
    ScheduleRecord
)


# ============================================================
# 默认约束配置 (统一管理)
# ============================================================

DEFAULT_CONSTRAINTS: List[dict] = [
    {"id": "daily_subject_limit", "type": "hard", "enabled": True, "weight": 10, "label": "每日同科目上限"},
    {"id": "main_morning", "type": "soft", "enabled": True, "weight": 8, "label": "主科优先上午"},
    {"id": "balanced_distribution", "type": "soft", "enabled": True, "weight": 6, "label": "科目周内均匀分布"},
    {"id": "artpe_not_first", "type": "soft", "enabled": True, "weight": 5, "label": "艺体课避开第1节"},
    {"id": "venue_dispersion", "type": "soft", "enabled": True, "weight": 4, "label": "场地使用分散"},
    {"id": "teacher_shift", "type": "soft", "enabled": True, "weight": 3, "label": "早晚班教师约束"},
    {"id": "meeting_reservation", "type": "soft", "enabled": True, "weight": 2, "label": "会议/教研时间预留"},
    {"id": "department_meeting", "type": "hard", "enabled": True, "weight": 7, "label": "教研组组会时间"},
    {"id": "admin_afternoon", "type": "hard", "enabled": True, "weight": 8, "label": "管理干部会议时间"},
]

DEFAULT_SOFT_CONFIG = DEFAULT_CONSTRAINTS  # 兼容旧引用

_ART_PE_KEYWORDS = {
    '体育', '美术', '音乐', '声乐', '钢琴', '轮滑', '舞蹈',
    '艺术', 'PE', 'Art', 'Music',
}


# ============================================================
# ScheduleSession
# ============================================================

@dataclass
class ScheduleSession:
    """排课决策单元（一次排课决策）"""
    id: int
    task_ids: List[int]
    teacher_ids: List[int]
    class_ids: List[int]
    subject_id: int
    subject_name: str
    duration: int                        # 1 = 单节, 2 = 连堂
    venue_type: Optional[str]
    layer_group_id: Optional[int]
    grades: List[str]
    is_main_subject: bool = False
    is_continuous_pair: bool = False      # 标记为「连堂对」
    department: str = "PRIMARY"           # 课程所属学部（用于跨学部教师时间约束）


# ============================================================
# SessionBuilder（修复连堂逻辑：每周恰好 1 次连堂）
# ============================================================

class SessionBuilder:
    """将 ScheduleData 转换为 ScheduleSession 列表"""

    def __init__(self, data: ScheduleData):
        self.data = data

    def build(self) -> List[ScheduleSession]:
        sessions: List[ScheduleSession] = []
        sid = 0
        layer_task_ids: Set[int] = set()

        # ---------- 1. 处理分层组 ----------
        for group in self.data.layer_groups:
            tasks = self.data.get_layer_tasks(group.id)
            if not tasks:
                continue

            teacher_ids = list({t.teacher_id for t in tasks})
            task_ids = [t.id for t in tasks]
            layer_task_ids.update(task_ids)

            affected_class_ids = list({t.class_id for t in tasks})

            # 标记受影响班级的同科目普通任务
            for t in self.data.tasks:
                if (t.id not in layer_task_ids
                        and t.class_id in affected_class_ids
                        and t.subject_id == group.subject_id):
                    layer_task_ids.add(t.id)

            grades = list(set(group.grades)) if group.grades else []
            subject = self.data.get_subject(group.subject_id)
            is_main = subject.is_main if subject else False
            venue_type = tasks[0].required_venue_type if tasks else None

            # 推断分层组所属学部（取第一个班级的学部）
            dept = "PRIMARY"
            if affected_class_ids:
                first_class = self.data.get_class(affected_class_ids[0])
                if first_class:
                    dept = first_class.department

            sid = self._create_sessions_for_hours(
                sessions, sid, task_ids, teacher_ids, affected_class_ids,
                group.subject_id, group.subject_name, group.weekly_hours,
                group.needs_continuous, venue_type, group.id, grades, is_main,
                dept,
            )

        # ---------- 2. 处理非分层任务 ----------
        for task in self.data.tasks:
            if task.id in layer_task_ids:
                continue

            cls = self.data.get_class(task.class_id)
            grade = cls.grade if cls else "G1"
            dept = cls.department if cls else "PRIMARY"
            subject = self.data.get_subject(task.subject_id)
            is_main = subject.is_main if subject else False

            sid = self._create_sessions_for_hours(
                sessions, sid, [task.id], [task.teacher_id], [task.class_id],
                task.subject_id, task.subject_name, task.weekly_hours,
                task.is_continuous, task.required_venue_type, None,
                [grade], is_main, dept,
            )

        self._print_diagnostics(sessions, layer_task_ids)
        return sessions

    def _create_sessions_for_hours(
        self, sessions: list, sid: int,
        task_ids: list, teacher_ids: list, class_ids: list,
        subject_id: int, subject_name: str, weekly_hours: int,
        needs_continuous: bool, venue_type: Optional[str],
        layer_group_id: Optional[int], grades: list, is_main: bool,
        department: str = "PRIMARY",
    ) -> int:
        """为指定课时数创建 sessions，处理连堂逻辑"""
        base = dict(
            task_ids=task_ids, teacher_ids=teacher_ids,
            class_ids=class_ids, subject_id=subject_id,
            subject_name=subject_name, venue_type=venue_type,
            layer_group_id=layer_group_id, grades=grades,
            is_main_subject=is_main, department=department,
        )

        if needs_continuous and weekly_hours >= 2:
            # 恰好 1 次连堂 (2 课时) + 剩余单节
            sessions.append(ScheduleSession(
                id=sid, duration=2, is_continuous_pair=True, **base
            ))
            sid += 1
            for _ in range(weekly_hours - 2):
                sessions.append(ScheduleSession(
                    id=sid, duration=1, is_continuous_pair=False, **base
                ))
                sid += 1
        else:
            for _ in range(weekly_hours):
                sessions.append(ScheduleSession(
                    id=sid, duration=1, is_continuous_pair=False, **base
                ))
                sid += 1
        return sid

    def _print_diagnostics(self, sessions: list, layer_task_ids: set):
        print(f"    构建完成: {len(sessions)} 个排课会话")
        print(f"    分层组覆盖任务: {len(layer_task_ids)} / {len(self.data.tasks)}")
        cont_count = sum(1 for s in sessions if s.is_continuous_pair)
        if cont_count:
            print(f"    连堂会话: {cont_count} 个")

        class_load: Dict[int, int] = defaultdict(int)
        for s in sessions:
            for cid in s.class_ids:
                class_load[cid] += s.duration

        overloaded = [(c, ld) for c, ld in class_load.items() if ld > 46]
        if overloaded:
            overloaded.sort(key=lambda x: -x[1])
            print(f"    WARNING 超载班级:")
            for cid, load in overloaded[:5]:
                c = self.data.get_class(cid)
                print(f"      {c.name if c else cid}: {load} 课时/周")


# ============================================================
# CPScheduleSolver
# ============================================================

class CPScheduleSolver:
    """基于 OR-Tools CP-SAT 的排课求解器（三层约束体系）"""

    def __init__(self, data: ScheduleData):
        self.data = data
        self.sessions: List[ScheduleSession] = []
        self.model = cp_model.CpModel()

        # x[session_id][(day, period)] = BoolVar
        self.x: Dict[int, Dict[Tuple[int, int], cp_model.IntVar]] = {}

        # 索引
        self._teacher_sessions: Dict[int, List[int]] = defaultdict(list)
        self._class_sessions: Dict[int, List[int]] = defaultdict(list)
        self._venue_sessions: Dict[str, List[int]] = defaultdict(list)
        self._class_subject_sessions: Dict[Tuple[int, int], List[int]] = defaultdict(list)

        # 场地容量（按科目名聚合）
        self._venue_capacities: Dict[str, int] = {}
        for venue in data.venues:
            for subj_name in venue.subjects:
                self._venue_capacities[subj_name] = (
                    self._venue_capacities.get(subj_name, 0) + venue.capacity
                )

        # 约束配置
        self._constraints: List[dict] = list(DEFAULT_CONSTRAINTS)
        # 会议预留时间槽 [{day, period, teacher_ids?}]
        self._meeting_slots: List[dict] = []
        # 诊断报告（无解时填充）
        self._diagnosis_report: Optional[dict] = None
        # 教研组组会决策变量 {group_id: {(day, period): BoolVar}}
        self._meeting_vars: Dict[int, Dict[Tuple[int, int], any]] = {}
        # 组会结果 {group_id: {"day": int, "period": int, "group_name": str}}
        self._meeting_results: Dict[int, dict] = {}

    # ----------------------------------------------------------
    # 主入口
    # ----------------------------------------------------------

    def solve(
        self,
        time_limit_seconds: int = 120,
        num_solutions: int = 1,
        constraints: Optional[List[dict]] = None,
        meeting_slots: Optional[List[dict]] = None,
        debug: bool = False,
        # 兼容旧参数名（如果仍然有调用传递 soft_config）
        soft_config: Optional[List[dict]] = None,
    ) -> List[List[ScheduleRecord]]:
        """
        求解排课问题

        Args:
            time_limit_seconds: 求解时间上限（秒）
            num_solutions: 生成方案数
            constraints: 约束配置列表
            meeting_slots: 会议预留时间槽
            debug: 是否开启求解器日志
        Returns:
            多方案排课记录列表
        """
        total_start = time.time()

        # 兼容处理：优先使用 constraints，其次 soft_config
        cfg_input = constraints or soft_config
        if cfg_input:
            # 合并配置，确保所有默认 ID 都在
            id_map = {c["id"]: c for c in cfg_input}
            self._constraints = []
            for default in DEFAULT_CONSTRAINTS:
                if default["id"] in id_map:
                    # 使用传入的配置，但确保有 type
                    user_cfg = id_map[default["id"]]
                    if "type" not in user_cfg:
                        # 如果没有 type，可能是旧格式，使用默认 type
                        user_cfg["type"] = default["type"]
                    self._constraints.append(user_cfg)
                else:
                    self._constraints.append(default)

        if meeting_slots:
            self._meeting_slots = meeting_slots

        # 1. 构建 sessions
        print("\n>>> [CP-SAT] 构建排课会话...")
        builder = SessionBuilder(self.data)
        self.sessions = builder.build()
        if not self.sessions:
            print("    WARNING: 没有排课会话可处理")
            return [[]]

        # 2. 构建索引
        self._build_indexes()

        # 3. 创建变量
        print(">>> [CP-SAT] 创建变量...")
        self._create_variables()
        total_vars = sum(len(sv) for sv in self.x.values())
        print(f"    {len(self.sessions)} 个会话, {total_vars} 个布尔变量")
        self._diagnose_slots()

        # 4. 硬约束（含 H1-H5）
        print(">>> [CP-SAT] 添加硬约束...")
        self._add_tier1_constraints()

        # 5. 业务约束 (可配置硬/软)
        print(">>> [CP-SAT] 应用业务约束...")
        self._apply_configurable_constraints()

        # 6. 求解
        print(f">>> [CP-SAT] 开始求解 (时间上限={time_limit_seconds}s)...")
        solutions = self._run_solver(time_limit_seconds, num_solutions, debug)

        elapsed = time.time() - total_start
        print(f">>> [CP-SAT] 求解完成, 耗时 {elapsed:.1f}s, 获得 {len(solutions)} 个方案")
        return solutions

    # ----------------------------------------------------------
    # 索引构建
    # ----------------------------------------------------------

    def _build_indexes(self):
        self._teacher_sessions = defaultdict(list)
        self._class_sessions = defaultdict(list)
        self._venue_sessions = defaultdict(list)
        self._class_subject_sessions = defaultdict(list)
        for s in self.sessions:
            for tid in s.teacher_ids:
                self._teacher_sessions[tid].append(s.id)
            for cid in s.class_ids:
                self._class_sessions[cid].append(s.id)
                self._class_subject_sessions[(cid, s.subject_id)].append(s.id)
            if s.venue_type and s.venue_type in self._venue_capacities:
                self._venue_sessions[s.venue_type].append(s.id)

        # 场地诊断日志
        skipped_venue_types = set()
        for s in self.sessions:
            if s.venue_type and s.venue_type not in self._venue_capacities:
                skipped_venue_types.add(s.venue_type)
        if skipped_venue_types:
            print(f"    场地跳过(未注册): {skipped_venue_types}")
        if self._venue_sessions:
            print(f"    场地约束生效:")
            for vt, sids in self._venue_sessions.items():
                cap = self._venue_capacities.get(vt, 0)
                print(f"      {vt}: {len(sids)} 个会话, 容量={cap}")

    # ----------------------------------------------------------
    # 变量创建
    # ----------------------------------------------------------

    def _create_variables(self):
        for s in self.sessions:
            valid_slots = self._get_valid_slots(s)
            slot_vars: Dict[Tuple[int, int], cp_model.IntVar] = {}
            for day, period in valid_slots:
                slot_vars[(day, period)] = self.model.NewBoolVar(
                    f"x_s{s.id}_d{day}_p{period}"
                )
            self.x[s.id] = slot_vars

    def _get_valid_slots(self, session: ScheduleSession) -> List[Tuple[int, int]]:
        """
        获取 Session 的合法起始槽位（仅 Tier-1 级别物理过滤）

        注意：艺体课第1节、教师早晚班 等已移至软约束，此处不过滤。
        """
        slots: List[Tuple[int, int]] = []
        for day in range(1, 6):
            max_period = self._get_max_period(day, session)
            for period in range(1, max_period + 1):
                end_period = period + session.duration - 1

                if end_period > max_period:
                    continue

                # 10-11 节只允许 G8/G9 周四
                if period >= 10 or end_period >= 10:
                    if day != 4 or not all(
                        g in ('G8', 'G9') for g in session.grades
                    ):
                        continue

                # 不跨 9-10 节边界
                if period <= 9 < end_period:
                    continue

                # 连堂不跨午休（5-6 节之间）
                if session.duration > 1 and period <= 5 < end_period:
                    continue

                # 教师时间可用性检查（硬约束）
                # 同时检查 unavailable_slots 和 daily_shifts，使用 session.department 进行学部感知
                available = True
                for p in range(period, end_period + 1):
                    for tid in session.teacher_ids:
                        teacher = self.data.get_teacher(tid)
                        if teacher:
                            if not teacher.is_available(day, p, session.department):
                                available = False
                                break
                    if not available:
                        break
                if not available:
                    continue

                slots.append((day, period))
        return slots

    def _get_max_period(self, day: int, session: ScheduleSession) -> int:
        """
        获取 session 在指定天的最大节次
        
        优先使用 time_slots 配置（学部感知），如果未加载则回退到硬编码逻辑。
        """
        # 优先使用配置化的时间槽数据
        if self.data.time_slots and session.department in self.data.time_slots:
            return self.data.time_slots[session.department].get_max_period(day)
        
        # 回退到硬编码逻辑（向后兼容）
        if day == 5:
            return 8
        if day == 4 and session.grades and all(g in ('G8', 'G9') for g in session.grades):
            return 11
        return 9

    @staticmethod
    def _is_art_pe(name: str) -> bool:
        return any(kw in name for kw in _ART_PE_KEYWORDS)

    # ----------------------------------------------------------
    # 诊断
    # ----------------------------------------------------------

    def _diagnose_slots(self):
        no_slots = [s for s in self.sessions if len(self.x[s.id]) == 0]
        few_slots = [(s, len(self.x[s.id]))
                     for s in self.sessions if 0 < len(self.x[s.id]) < 3]

        if no_slots:
            print(f"    WARNING {len(no_slots)} 个会话无合法槽位:")
            for s in no_slots[:5]:
                t_names = [self.data.get_teacher(t).name
                           for t in s.teacher_ids
                           if self.data.get_teacher(t)]
                print(f"      Session {s.id}: {s.subject_name}, "
                      f"教师={t_names}, 班级={s.class_ids}, "
                      f"时长={s.duration}, 年级={s.grades}")
        if few_slots:
            print(f"    WARNING {len(few_slots)} 个会话槽位不足 3:")
            for s, n in few_slots[:5]:
                print(f"      Session {s.id}: {s.subject_name}, 可用={n}")

        teacher_load: Dict[int, int] = defaultdict(int)
        class_load: Dict[int, int] = defaultdict(int)
        for s in self.sessions:
            for tid in s.teacher_ids:
                teacher_load[tid] += s.duration
            for cid in s.class_ids:
                class_load[cid] += s.duration

        if teacher_load:
            bt = max(teacher_load, key=teacher_load.get)
            t = self.data.get_teacher(bt)
            print(f"    教师最大负载: {t.name if t else bt} = "
                  f"{teacher_load[bt]} 课时/周")
        if class_load:
            bc = max(class_load, key=class_load.get)
            c = self.data.get_class(bc)
            print(f"    班级最大负载: {c.name if c else bc} = "
                  f"{class_load[bc]} 课时/周")

    # ===========================================================
    #  Tier 1: 物理硬约束（违反 = 无效解）
    # ===========================================================

    def _add_tier1_constraints(self):
        self._h1_exactly_one()
        self._h2_teacher_no_conflict()
        self._h3_class_no_conflict()
        self._h4_venue_capacity()
        # H5 已移至可配置约束中处理

    def _h1_exactly_one(self):
        """H1: 每个 Session 恰好安排到一个槽位"""
        skipped = 0
        for s in self.sessions:
            slot_vars = list(self.x[s.id].values())
            if not slot_vars:
                skipped += 1
                continue
            self.model.AddExactlyOne(slot_vars)
        if skipped:
            print(f"    H1: 跳过 {skipped} 个无槽位会话")

    def _h2_teacher_no_conflict(self):
        """H2: 同一教师同一时刻最多 1 节课"""
        count = 0
        for tid, sids in self._teacher_sessions.items():
            if len(sids) < 2:
                continue
            slot_map: Dict[Tuple[int, int], List] = defaultdict(list)
            for sid in sids:
                s = self.sessions[sid]
                for (day, period), var in self.x[sid].items():
                    for p in range(period, period + s.duration):
                        slot_map[(day, p)].append(var)
            for _, vl in slot_map.items():
                if len(vl) > 1:
                    self.model.Add(sum(vl) <= 1)
                    count += 1
        print(f"    H2: 教师无冲突 {count} 条")

    def _h3_class_no_conflict(self):
        """H3: 同一班级同一时刻最多 1 节课"""
        count = 0
        for cid, sids in self._class_sessions.items():
            if len(sids) < 2:
                continue
            slot_map: Dict[Tuple[int, int], List] = defaultdict(list)
            for sid in sids:
                s = self.sessions[sid]
                for (day, period), var in self.x[sid].items():
                    for p in range(period, period + s.duration):
                        slot_map[(day, p)].append(var)
            for _, vl in slot_map.items():
                if len(vl) > 1:
                    self.model.Add(sum(vl) <= 1)
                    count += 1
        print(f"    H3: 班级无冲突 {count} 条")

    def _h4_venue_capacity(self):
        """H4: 场地容量上限"""
        count = 0
        for vtype, sids in self._venue_sessions.items():
            cap = self._venue_capacities.get(vtype, 1)
            if len(sids) <= cap:
                continue
            slot_map: Dict[Tuple[int, int], List] = defaultdict(list)
            for sid in sids:
                s = self.sessions[sid]
                for (day, period), var in self.x[sid].items():
                    for p in range(period, period + s.duration):
                        slot_map[(day, p)].append(var)
            for _, vl in slot_map.items():
                if len(vl) > cap:
                    self.model.Add(sum(vl) <= cap)
                    count += 1
        print(f"    H4: 场地容量 {count} 条")

    # ===========================================================
    #  业务规则实现 (支持 Hard/Soft 切换)
    # ===========================================================

    def _apply_configurable_constraints(self):
        objective_terms = []

        dispatch = {
            "daily_subject_limit": self._rule_daily_subject_limit,
            "main_morning": self._rule_main_morning,
            "balanced_distribution": self._rule_balanced_distribution,
            "artpe_not_first": self._rule_artpe_not_first,
            "venue_dispersion": self._rule_venue_dispersion,
            "teacher_shift": self._rule_teacher_shift,
            "meeting_reservation": self._rule_meeting_reservation,
            "department_meeting": self._rule_department_meeting,
            "admin_afternoon": self._rule_admin_afternoon,
        }

        print(f"    约束配置共 {len(self._constraints)} 项:")
        for cfg in self._constraints:
            cid = cfg.get("id", "?")
            enabled = cfg.get("enabled", True)
            ctype = cfg.get("type", "soft")
            print(f"      {cid}: enabled={enabled}, type={ctype}, weight={cfg.get('weight', '?')}")

            if not enabled:
                continue

            weight = cfg.get("weight", 5) * 10
            handler = dispatch.get(cid)
            if handler:
                handler(ctype, weight, objective_terms)
            else:
                print(f"      WARNING: 未知约束 ID '{cid}'，跳过")

        if objective_terms:
            self.model.Maximize(sum(objective_terms))
            print(f"    目标函数: {len(objective_terms)} 个优化项")
        else:
            print(f"    WARNING: 无软约束优化项")

    # ---------- R1: 每日同科目上限 (原 H5) ----------

    def _rule_daily_subject_limit(self, ctype: str, weight: int, terms: list):
        """每班每天同一科目最多 2 课时"""
        count = 0
        for (cid, subj_id), sids in self._class_subject_sessions.items():
            if len(sids) < 2:
                continue
            for day in range(1, 6):
                day_vars = []
                for sid in sids:
                    s = self.sessions[sid]
                    for (d, p), var in self.x[sid].items():
                        if d == day:
                            day_vars.append((var, s.duration))
                
                if not day_vars:
                    continue

                total_duration = sum(v * dur for v, dur in day_vars)

                if ctype == "hard":
                    self.model.Add(total_duration <= 2)
                else:
                    # 软约束: 超过 2 节扣分
                    # excess >= total - 2
                    excess = self.model.NewIntVar(0, 10, f"exc_h5_{cid}_{subj_id}_{day}")
                    self.model.Add(excess >= total_duration - 2)
                    terms.append(-excess * weight)
                count += 1
        print(f"    规则 [每日同科目上限]: {ctype.upper()}, 检查了 {count} 组")

    # ---------- R2: 主科优先上午 (原 S1) ----------

    def _rule_main_morning(self, ctype: str, weight: int, terms: list):
        count = 0
        for s in self.sessions:
            if not s.is_main_subject:
                continue
            
            afternoon_vars = []
            morning_vars = []
            for (day, period), var in self.x[s.id].items():
                if period > 5:
                    afternoon_vars.append(var)
                else:
                    morning_vars.append(var)

            if ctype == "hard":
                if afternoon_vars:
                    self.model.Add(sum(afternoon_vars) == 0)
                count += 1
            else:
                if morning_vars:
                    terms.append(sum(morning_vars) * weight)
                    count += 1
        print(f"    规则 [主科上午]: {ctype.upper()}, 涉及 {count} 项")

    # ---------- R3: 科目周内均匀分布 (原 S2) ----------

    def _rule_balanced_distribution(self, ctype: str, weight: int, terms: list):
        count = 0
        for (cid, subj_id), sids in self._class_subject_sessions.items():
            if len(sids) <= 1:
                continue
            
            for day in range(1, 6):
                day_vars = []
                for sid in sids:
                    for (d, _), var in self.x[sid].items():
                        if d == day:
                            day_vars.append(var)
                
                if len(day_vars) > 1:
                    if ctype == "hard":
                         self.model.Add(sum(day_vars) <= 1)
                    else:
                        has_any = self.model.NewBoolVar(f"bal_{cid}_{subj_id}_{day}")
                        self.model.Add(sum(day_vars) >= 1).OnlyEnforceIf(has_any)
                        self.model.Add(sum(day_vars) == 0).OnlyEnforceIf(has_any.Not())
                        
                        terms.append(has_any * weight)
                        for v in day_vars:
                            terms.append(-v * weight)
                count += 1
        print(f"    规则 [均匀分布]: {ctype.upper()}, 检查 {count} 组")

    # ---------- R4: 艺体课避开第1节 (原 S3) ----------

    def _rule_artpe_not_first(self, ctype: str, weight: int, terms: list):
        count = 0
        for s in self.sessions:
            if not self._is_art_pe(s.subject_name):
                continue
            
            first_period_vars = []
            for (day, period), var in self.x[s.id].items():
                if period == 1:
                    first_period_vars.append(var)
            
            if not first_period_vars:
                continue

            if ctype == "hard":
                self.model.Add(sum(first_period_vars) == 0)
            else:
                terms.append(-sum(first_period_vars) * weight)
            count += 1
        print(f"    规则 [艺体非首节]: {ctype.upper()}, 涉及 {count} 项")

    # ---------- R5: 场地使用分散 (原 S4) ----------
    
    def _rule_venue_dispersion(self, ctype: str, weight: int, terms: list):
        count = 0
        for vtype, sids in self._venue_sessions.items():
            cap = self._venue_capacities.get(vtype, 1)
            if len(sids) <= cap:
                continue
                
            slot_map: Dict[Tuple[int, int], List] = defaultdict(list)
            for sid in sids:
                s = self.sessions[sid]
                for (day, period), var in self.x[sid].items():
                     for p in range(period, period + s.duration):
                        slot_map[(day, p)].append(var)
            
            for _, vl in slot_map.items():
                if len(vl) > 1:
                    if ctype == "hard":
                         # 强制同一时间只能用 1 个
                         self.model.Add(sum(vl) <= 1)
                    else:
                        for v in vl:
                             terms.append(-v * (weight // 2))
                    count += 1
        print(f"    规则 [场地分散]: {ctype.upper()}, 涉及 {count} 组")

    # ---------- R6: 早晚班教师 (原 S5) ----------

    def _rule_teacher_shift(self, ctype: str, weight: int, terms: list):
        count = 0
        for s in self.sessions:
            for tid in s.teacher_ids:
                teacher = self.data.get_teacher(tid)
                if not teacher: continue
                
                bad_vars = []
                for (day, period), var in self.x[s.id].items():
                     shift = teacher.daily_shifts.get(str(day), "morning")
                     if shift == "evening":
                         # 使用 session 所属学部判断班次限制（支持跨学部教师）
                         effective_dept = s.department or teacher.department
                         limit = 5 if effective_dept == "PRIMARY" else 4
                         if period <= limit:
                             bad_vars.append(var)
                
                if not bad_vars: continue

                if ctype == "hard":
                    self.model.Add(sum(bad_vars) == 0)
                else:
                    terms.append(-sum(bad_vars) * weight)
                count += 1
        print(f"    规则 [早晚班]: {ctype.upper()}, 涉及 {count} 项")

    # ---------- R7: 会议预留 (原 S6) ----------
    
    def _rule_meeting_reservation(self, ctype: str, weight: int, terms: list):
        if not self._meeting_slots: return
        count = 0
        for slot_cfg in self._meeting_slots:
            m_day = slot_cfg.get("day")
            m_period = slot_cfg.get("period")
            m_tids = set(slot_cfg.get("teacher_ids", []))
            if m_day is None or m_period is None: continue
            
            for s in self.sessions:
                conflict_vars = []
                for (day, period), var in self.x[s.id].items():
                     if day != m_day: continue
                     # 检查时间段重叠
                     if period <= m_period < period + s.duration:
                         if not m_tids or (set(s.teacher_ids) & m_tids):
                             conflict_vars.append(var)
                
                if not conflict_vars: continue
                
                if ctype == "hard":
                    self.model.Add(sum(conflict_vars) == 0)
                else:
                    terms.append(-sum(conflict_vars) * weight)
                count += 1
        print(f"    规则 [会议预留]: {ctype.upper()}, 涉及 {count} 项")

    def _rule_department_meeting(self, ctype: str, weight: int, terms: list):
        """
        教研组组会约束：同一教研组的所有教师每周须有 2 节连续空闲时段用于组会。
        合法时段对（不跨午休 5-6）: (1,2),(2,3),(3,4),(4,5),(6,7),(7,8),(8,9)
        """
        # 按 research_group_id 分组教师
        group_teachers: Dict[int, List[int]] = defaultdict(list)
        group_names: Dict[int, str] = {}
        for t in self.data.teachers:
            gid = t.research_group_id
            if gid:
                group_teachers[gid].append(t.id)
                if gid not in group_names:
                    group_names[gid] = f"教研组{gid}"

        # 尝试从 DB 获取教研组名称
        try:
            from app.core.database import SessionLocal
            from app.modules.teachers.models import ResearchGroup
            db = SessionLocal()
            for rg in db.query(ResearchGroup).filter(
                ResearchGroup.is_deleted == False
            ).all():
                if rg.id in group_names:
                    group_names[rg.id] = rg.name
            db.close()
        except Exception:
            pass

        # 合法的组会起始节次（组会占 2 节，不跨 5-6 午休边界）
        valid_starts = [1, 2, 3, 4, 6, 7, 8]
        total_constraints = 0

        for gid, tids in group_teachers.items():
            if len(tids) < 2:
                continue

            # 收集该组所有教师的 session id（使用预建索引，避免遍历所有 sessions）
            group_sids: Set[int] = set()
            for tid in tids:
                for sid in self._teacher_sessions.get(tid, []):
                    group_sids.add(sid)

            # 创建组会选择变量: meeting_g_d_p
            meeting_vars = {}
            for day in range(1, 6):
                for p in valid_starts:
                    var = self.model.NewBoolVar(f"meet_g{gid}_d{day}_p{p}")
                    meeting_vars[(day, p)] = var

            self._meeting_vars[gid] = meeting_vars

            if ctype == "hard":
                # 恰好选 1 个组会时段
                self.model.AddExactlyOne(list(meeting_vars.values()))
            else:
                # 软约束: 至多 1 个, 尽量选
                self.model.Add(sum(meeting_vars.values()) <= 1)
                terms.append(sum(meeting_vars.values()) * weight)

            # 当组会时段被选中时，该组所有教师在那 2 节不能有课
            for (day, p_start), m_var in meeting_vars.items():
                for sid in group_sids:
                    s = self.sessions[sid]
                    for target_p in [p_start, p_start + 1]:
                        # 找到所有可能占据 target_p 的起始时刻
                        for (d, p), x_var in self.x[sid].items():
                            if d != day:
                                continue
                            # session 从 p 开始，占据 [p, p+duration-1]
                            if p <= target_p < p + s.duration:
                                # m_var=1 => x_var=0
                                self.model.Add(x_var == 0).OnlyEnforceIf(m_var)
                                total_constraints += 1

        active_groups = sum(1 for tids in group_teachers.values() if len(tids) >= 2)
        print(f"    规则 [教研组组会]: {ctype.upper()}, "
              f"{active_groups} 个活跃教研组, {total_constraints} 条指示约束")

    def _rule_admin_afternoon(self, ctype: str, weight: int, terms: list):
        """
        管理干部会议时间约束：
        - 小学管理干部(PRIMARY_ADMIN): 周一下午(day=1, periods 6-9)不排课
        - 中学管理干部(SECONDARY_ADMIN): 周二下午(day=2, periods 6-9)不排课
        """
        AFTERNOON_PERIODS = [6, 7, 8, 9]
        # 规则: (tag, day)
        rules = [
            ("PRIMARY_ADMIN", 1),   # 小学管理干部 → 周一下午
            ("SECONDARY_ADMIN", 2), # 中学管理干部 → 周二下午
        ]

        # 收集每个规则涉及的教师 ID
        tag_tids: Dict[str, Set[int]] = {}
        for tag, _ in rules:
            tag_tids[tag] = set()

        for t in self.data.teachers:
            for tag, _ in rules:
                if tag in (t.tags or []):
                    tag_tids[tag].add(t.id)

        count = 0
        for tag, blocked_day in rules:
            tids = tag_tids[tag]
            if not tids:
                continue
            for s in self.sessions:
                if not (set(s.teacher_ids) & tids):
                    continue
                for (day, period), var in self.x[s.id].items():
                    if day != blocked_day:
                        continue
                    # 检查 session 是否占据下午时段
                    occupied = range(period, period + s.duration)
                    if any(p in AFTERNOON_PERIODS for p in occupied):
                        if ctype == "hard":
                            self.model.Add(var == 0)
                        else:
                            terms.append(-var * weight)
                        count += 1

        print(f"    规则 [管理干部会议]: {ctype.upper()}, {count} 条约束")

    # ===========================================================
    #  求解 & 诊断
    # ===========================================================

    def _run_solver(
        self, time_limit: int, num_solutions: int, debug: bool = False,
    ) -> List[List[ScheduleRecord]]:
        solutions: List[List[ScheduleRecord]] = []

        # 多方案时每个方案分配的时间 = 总时间 / 方案数（至少30秒）
        per_solution_limit = max(30, time_limit) if num_solutions <= 1 \
            else max(30, time_limit // num_solutions)

        # 使用时间戳生成随机种子基数，确保每次运行结果不同
        seed_base = int(time.time()) % 100000

        for idx in range(num_solutions):
            if idx > 0:
                self._rebuild_model_for_diversity(solutions, idx)

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = (
                time_limit if idx == 0 else per_solution_limit
            )
            if debug:
                solver.parameters.log_search_progress = True

            solver.parameters.num_workers = 0  # 0 = 自动检测并使用所有可用核心
            solver.parameters.random_seed = seed_base + idx * 37

            status = solver.Solve(self.model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                records = self._extract_solution(solver)
                solutions.append(records)
                sname = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
                try:
                    obj = solver.ObjectiveValue()
                except Exception:
                    obj = 0
                print(f"    方案 {idx+1}: {sname}, 目标值={obj:.1f}, "
                      f"记录={len(records)}")
            else:
                status_names = {
                    cp_model.INFEASIBLE: "INFEASIBLE (无解)",
                    cp_model.MODEL_INVALID: "MODEL_INVALID",
                    cp_model.UNKNOWN: "UNKNOWN (超时)",
                }
                print(f"    方案 {idx+1}: "
                      f"{status_names.get(status, f'STATUS={status}')}")

                if status == cp_model.INFEASIBLE and idx == 0:
                    # 第一个方案就无解，启动逐层诊断（仅分析，不产出降级方案）
                    print(f"    方案 {idx+1}: 无解 (INFEASIBLE). 启动逐层诊断...")
                    self._diagnosis_report = self._diagnose_infeasibility()
                    break
                # 非首个方案失败：不退出循环，继续尝试（用不同种子重试一次）
                if idx > 0:
                    print(f"    方案 {idx+1}: 降低多样性要求后重试...")
                    self._rebuild_model_for_diversity(
                        solutions, idx, lenient=True
                    )
                    solver2 = cp_model.CpSolver()
                    solver2.parameters.max_time_in_seconds = per_solution_limit
                    if debug:
                        solver2.parameters.log_search_progress = True
                    solver2.parameters.num_workers = 0
                    solver2.parameters.random_seed = seed_base + idx * 37 + 7
                    status2 = solver2.Solve(self.model)
                    if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                        records = self._extract_solution(solver2)
                        solutions.append(records)
                        print(f"    方案 {idx+1}: 重试成功, "
                              f"记录={len(records)}")
                    else:
                        print(f"    方案 {idx+1}: 重试仍然失败, 跳过")

        return solutions

    # ----------------------------------------------------------
    # 诊断无解（仅分析，不产出降级方案）
    # ----------------------------------------------------------

    def _diagnose_infeasibility(self) -> dict:
        """
        逐层添加约束来定位冲突源。

        思路：从最小约束集 (H1) 开始，逐步叠加约束，
        每次测试是否可行。第一次变为 INFEASIBLE 的那一层就是冲突源。

        返回诊断报告 dict:
            passed: list[str]  — 通过的约束层
            failed: str | None — 导致无解的约束层名称
            suggestion: str    — 建议信息
        """
        print("\n" + "=" * 50)
        print(">>> [诊断] 开始逐层约束分析（仅诊断，不产出方案）")
        print("=" * 50)

        report = {"passed": [], "failed": None, "suggestion": ""}

        # 定义诊断层（按添加顺序）
        layers = [
            ("H1: 课程必须排入", [self._h1_exactly_one]),
            ("H2: 教师无冲突", [self._h2_teacher_no_conflict]),
            ("H3: 班级无冲突", [self._h3_class_no_conflict]),
            ("H4: 场地容量", [self._h4_venue_capacity]),
        ]

        # 收集可配置的硬约束
        hard_rules = []
        for cfg in self._constraints:
            if not cfg.get("enabled", True):
                continue
            if cfg.get("type", "soft") != "hard":
                continue
            cid = cfg["id"]
            dispatch = {
                "daily_subject_limit": self._rule_daily_subject_limit,
                "main_morning": self._rule_main_morning,
                "balanced_distribution": self._rule_balanced_distribution,
                "artpe_not_first": self._rule_artpe_not_first,
                "venue_dispersion": self._rule_venue_dispersion,
                "teacher_shift": self._rule_teacher_shift,
                "meeting_reservation": self._rule_meeting_reservation,
                "department_meeting": self._rule_department_meeting,
                "admin_afternoon": self._rule_admin_afternoon,
            }
            handler = dispatch.get(cid)
            if handler:
                label = cfg.get("label", cid)
                hard_rules.append((f"业务硬约束 [{label}]", cid, handler, cfg))

        for label, cid, handler, cfg in hard_rules:
            weight = cfg.get("weight", 5) * 10
            layers.append((
                label,
                # 包装成无参调用：硬约束模式，忽略 objective_terms
                [lambda h=handler, w=weight: h("hard", w, [])],
            ))

        # 逐层测试
        accumulated_fns = []
        for layer_name, fns in layers:
            accumulated_fns.extend(fns)
            # 重建模型
            self.model = cp_model.CpModel()
            self.x = {}
            self._create_variables()
            # 应用已累积的约束
            for fn in accumulated_fns:
                fn()

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30
            solver.parameters.num_workers = 0
            status = solver.Solve(self.model)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                report["passed"].append(layer_name)
                print(f"    ✓ {layer_name} — 可行")
            else:
                report["failed"] = layer_name
                status_name = {
                    cp_model.INFEASIBLE: "INFEASIBLE",
                    cp_model.UNKNOWN: "UNKNOWN (超时)",
                }.get(status, str(status))
                print(f"    ✗ {layer_name} — {status_name} ← 此约束导致无解!")
                break

        # 生成建议
        if report["failed"]:
            f = report["failed"]
            if "教师" in f:
                report["suggestion"] = "教师课时冲突: 某教师的总课时超过了可用时段。请检查教师的不可用时间和总课时量。"
            elif "班级" in f:
                report["suggestion"] = "班级课时冲突: 某班级的总课时超过了可用时段(含选修/周五限制)。"
            elif "场地" in f:
                report["suggestion"] = "场地容量不足: 需要该场地的课程太多, 同一时间段超过了场地数量上限。"
            elif "同科目" in f:
                report["suggestion"] = "每日同科目上限过严: 某科目周课时多(如9节), 在5天内每天<=2节无法排完。建议将此约束切换为[软约束]。"
            elif "主科" in f:
                report["suggestion"] = "主科强制上午导致无解: 上午时段不够安排所有主科。建议切换为[软约束]。"
            elif "均匀" in f:
                report["suggestion"] = "科目均匀分布强制每天<=1节, 但周课时>5的科目无法满足。建议切换为[软约束]。"
            elif "艺体" in f:
                report["suggestion"] = "艺体课避开首节与排课需求冲突。建议切换为[软约束]。"
            elif "场地分散" in f:
                report["suggestion"] = "场地分散限制太严(强制同时刻只能用1个), 但课程需求超出。建议切换为[软约束]。"
            elif "早晚班" in f:
                report["suggestion"] = "早晚班硬约束与教师可用时段冲突。建议切换为[软约束]。"
            elif "管理干部" in f:
                report["suggestion"] = "管理干部会议时间导致无解: 管理干部课时太多, 周一/周二下午无法全部空出。建议切换为[软约束]。"
            elif "组会" in f:
                report["suggestion"] = "教研组组会约束导致无解: 某教研组教师太多或课时太满, 找不到2节连续空闲。建议切换为[软约束]。"
            elif "会议" in f:
                report["suggestion"] = "会议预留时间与排课冲突。建议减少预留时段或切换为[软约束]。"
            else:
                report["suggestion"] = f"约束 '{f}' 导致无解, 建议将其切换为[软约束]或检查相关数据。"
        else:
            report["suggestion"] = "所有单层约束均可行，但组合后无解。可能是多条约束交叉冲突。建议逐个将业务硬约束切换为软约束来定位。"

        print(f"\n>>> [诊断] 结论: {report['failed'] or '组合冲突'}")
        print(f"    建议: {report['suggestion']}")
        print("=" * 50)
        return report

    # ----------------------------------------------------------
    # 多样性方案
    # ----------------------------------------------------------

    def _rebuild_model_for_diversity(
        self, prev_solutions: List[List[ScheduleRecord]], idx: int,
        lenient: bool = False,
    ):
        """重建模型并添加多样性约束

        Args:
            prev_solutions: 已有的方案列表
            idx: 当前方案索引
            lenient: 宽松模式，降低多样性要求（至少 5% 不同）
        """
        # 预建 task_id -> sessions 映射，避免 O(n²) 嵌套循环
        from collections import defaultdict
        task_to_sessions: Dict[int, List[ScheduleSession]] = defaultdict(list)
        for s in self.sessions:
            for tid in s.task_ids:
                task_to_sessions[tid].append(s)

        prev_assignments: List[Dict[int, Tuple[int, int]]] = []
        for records in prev_solutions:
            assignment: Dict[int, Tuple[int, int]] = {}
            seen_sessions: Set[int] = set()
            for r in records:
                for s in task_to_sessions.get(r.task_id, []):
                    if s.id not in seen_sessions:
                        assignment[s.id] = (r.day, r.period)
                        seen_sessions.add(s.id)
                        break
            prev_assignments.append(assignment)

        self.model = cp_model.CpModel()
        self.x = {}
        self._create_variables()
        self._add_tier1_constraints()
        self._apply_configurable_constraints()

        # 多样性比例：正常模式 10%，宽松模式 5%
        diff_ratio = 20 if lenient else 10

        for prev in prev_assignments:
            same_vars = []
            for sid, (day, period) in prev.items():
                if (day, period) in self.x.get(sid, {}):
                    same_vars.append(self.x[sid][(day, period)])
            if same_vars:
                min_diff = max(1, len(same_vars) // diff_ratio)
                self.model.Add(sum(same_vars) <= len(same_vars) - min_diff)

    # ----------------------------------------------------------
    # 结果提取
    # ----------------------------------------------------------

    def _extract_solution(
        self, solver: cp_model.CpSolver
    ) -> List[ScheduleRecord]:
        records: List[ScheduleRecord] = []
        for s in self.sessions:
            assigned_day = None
            assigned_period = None
            for (day, period), var in self.x[s.id].items():
                if solver.Value(var):
                    assigned_day = day
                    assigned_period = period
                    break
            if assigned_day is None:
                continue

            for task_id in s.task_ids:
                task = self.data.get_task(task_id)
                if not task:
                    continue
                for p_off in range(s.duration):
                    records.append(ScheduleRecord(
                        task_id=task_id,
                        teacher_id=task.teacher_id,
                        class_id=task.class_id,
                        subject_id=task.subject_id,
                        day=assigned_day,
                        period=assigned_period + p_off,
                        duration=1,
                        layer_group_id=s.layer_group_id,
                    ))

        # 读取教研组组会结果
        self._meeting_results = {}
        for gid, vars_dict in self._meeting_vars.items():
            for (day, period), m_var in vars_dict.items():
                if solver.Value(m_var):
                    self._meeting_results[gid] = {
                        "day": day,
                        "period": period,
                    }
                    break

        return records
