"""
排课引擎总控 (CP-SAT)

负责协调整个排课流程：
1. 加载数据
2. 读取约束配置
3. 调用 CP-SAT 求解器
4. 保存结果到数据库
5. 自动清理旧方案（保留最近 6 批）
6. 返回结果摘要
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Union
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from .data.loader import load_schedule_data
from .data.models import ScheduleRecord, ScheduleData
from .solver import CPScheduleSolver, DEFAULT_SOFT_CONFIG
from ..modules.schedules.models import Schedule, ScheduleItem, ScheduleConfig


MAX_BATCHES = 6  # 最多保留的排课批次数


class ScheduleEngine:
    """排课引擎总控"""

    def __init__(self, db: Session):
        self.db = db
        self.data: ScheduleData = None

    def run(
        self,
        optimization: int = 3,
        plan_count: int = 1,
        scope: str = "all",
        grades: List[str] = None,
        class_ids: List[int] = None,
        keep_manual: bool = False,
        debug: bool = False,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """执行排课"""
        print("=" * 50)
        print(">>> 排课引擎启动 (CP-SAT v2)")
        print(f"    优化程度: {optimization}, 方案数: {plan_count}, 范围: {scope}, Debug: {debug}")
        print("=" * 50)

        start_time = datetime.now()

        # 0. 自动清理旧方案
        self._cleanup_old_batches()

        # 1. 加载排课数据
        print("\n>>> 加载排课数据...")
        self.data = load_schedule_data(self.db)
        print(f"    教师: {len(self.data.teachers)}")
        print(f"    班级: {len(self.data.classes)}")
        print(f"    科目: {len(self.data.subjects)}")
        print(f"    任务: {len(self.data.tasks)}")
        print(f"    分层组: {len(self.data.layer_groups)}")
        print(f"    场地: {len(self.data.venues)}")

        # 2. 读取约束配置
        constraints, meeting_slots = self._load_constraint_config()

        # 3. 计算求解时间
        time_limits = {1: 30, 2: 60, 3: 120, 4: 300, 5: 600}
        time_limit = time_limits.get(optimization, 120)

        # 4. 求解
        solver = CPScheduleSolver(self.data)
        solutions = solver.solve(
            time_limit_seconds=time_limit,
            num_solutions=plan_count,
            constraints=constraints,
            meeting_slots=meeting_slots,
            debug=debug,
        )

        if not solutions or all(len(s) == 0 for s in solutions):
            # 收集诊断信息
            diag = solver._diagnosis_report
            if diag and diag.get("failed"):
                detail = (
                    f"排课无解。冲突源: {diag['failed']}。"
                    f"建议: {diag.get('suggestion', '请检查约束设置')}"
                )
            else:
                detail = "排课失败：求解器未能找到可行解，请检查数据配置或约束设置"
            raise RuntimeError(detail)

        # 5. 保存结果（含组会信息）
        meeting_info = getattr(solver, '_meeting_results', None) or {}
        # 转换 key 为字符串以便 JSON 序列化
        meeting_json = {str(k): v for k, v in meeting_info.items()} if meeting_info else None
        batch_id = str(uuid.uuid4())[:8]
        plans = []
        for i, records in enumerate(solutions):
            if not records:
                continue
            suffix = f"_方案{chr(65 + i)}" if plan_count > 1 else ""
            summary = self._build_summary(records, 0)
            schedule_id = self._save_results(
                records, suffix, batch_id, summary["score"],
                meeting_info=meeting_json,
            )
            summary["schedule_id"] = schedule_id
            plans.append(summary)

        plans.sort(key=lambda p: p["score"], reverse=True)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        for i, plan in enumerate(plans):
            plan["duration_seconds"] = round(duration / max(len(plans), 1), 1)
            plan["recommended"] = (i == 0)

        print("=" * 50)
        print(f">>> 排课完成, 耗时 {duration:.1f}s, {len(plans)} 个方案")
        if plans:
            print(f"    最佳方案得分: {plans[0]['score']}")
        print("=" * 50)

        if plan_count <= 1 and len(plans) == 1:
            plans[0]["duration_seconds"] = round(duration, 1)
            return plans[0]
        return plans

    # ----------------------------------------------------------
    # 约束配置
    # ----------------------------------------------------------

    def _load_constraint_config(self):
        """从数据库加载活跃的约束配置"""
        cfg = self.db.query(ScheduleConfig).filter(
            ScheduleConfig.is_active == True
        ).first()

        if cfg and cfg.config_json:
            data = cfg.config_json
            # 优先读取 constraints，兼容 soft_constraints（注意空列表判断）
            constraints = data.get("constraints")
            if not constraints:
                constraints = data.get("soft_constraints")
            if not constraints:
                constraints = list(DEFAULT_SOFT_CONFIG)
            meeting_slots = data.get("meeting_slots", [])
            print(f"    已加载约束配置: {cfg.name}, 约束项数: {len(constraints)}")
        else:
            constraints = list(DEFAULT_SOFT_CONFIG)
            meeting_slots = []
            print("    使用默认约束配置")

        return constraints, meeting_slots

    # ----------------------------------------------------------
    # 保存结果
    # ----------------------------------------------------------

    def _save_results(
        self, records: List[ScheduleRecord],
        suffix: str, batch_id: str, score: int,
        meeting_info: dict = None,
    ) -> int:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        schedule = Schedule(
            name=f"课表_{timestamp}{suffix}",
            is_active=False,
            batch_id=batch_id,
            score=score,
            meeting_info=meeting_info,
        )
        self.db.add(schedule)
        self.db.flush()

        for record in records:
            self.db.add(ScheduleItem(
                schedule_id=schedule.id,
                task_id=record.task_id,
                teacher_id=record.teacher_id,
                class_id=record.class_id,
                subject_id=record.subject_id,
                day=record.day,
                period=record.period,
            ))

        self.db.commit()
        print(f"    课表已保存, ID={schedule.id}, batch={batch_id}")
        return schedule.id

    # ----------------------------------------------------------
    # 自动清理
    # ----------------------------------------------------------

    def _cleanup_old_batches(self):
        """保留最近 MAX_BATCHES 批排课结果，旧的自动清理"""
        # 查询所有不同的 batch_id（排除空值和已激活方案的 batch）
        active_batches = set()
        active_schedules = self.db.query(Schedule).filter(
            Schedule.is_active == True
        ).all()
        for s in active_schedules:
            if s.batch_id:
                active_batches.add(s.batch_id)

        # 获取所有 batch_id 及其最新时间
        batches = (
            self.db.query(
                Schedule.batch_id,
                func.max(Schedule.created_at).label("latest"),
            )
            .filter(
                Schedule.batch_id.isnot(None),
                Schedule.batch_id.notin_(active_batches) if active_batches else True,
            )
            .group_by(Schedule.batch_id)
            .order_by(func.max(Schedule.created_at).desc())
            .all()
        )

        if len(batches) <= MAX_BATCHES:
            return

        # 需要删除的批次
        to_delete = [b.batch_id for b in batches[MAX_BATCHES:]]
        if not to_delete:
            return

        print(f">>> 清理旧方案: 删除 {len(to_delete)} 个历史批次")
        for bid in to_delete:
            old_schedules = self.db.query(Schedule).filter(
                Schedule.batch_id == bid
            ).all()
            for s in old_schedules:
                self.db.query(ScheduleItem).filter(
                    ScheduleItem.schedule_id == s.id
                ).delete()
                self.db.delete(s)
        self.db.commit()

    # ----------------------------------------------------------
    # 评分
    # ----------------------------------------------------------

    def _build_summary(
        self, records: List[ScheduleRecord], schedule_id: int,
    ) -> Dict[str, Any]:
        total_tasks = len(self.data.tasks)
        scheduled_ids = {r.task_id for r in records}
        scheduled_tasks = len({
            tid for tid in scheduled_ids if self.data.get_task(tid)
        })
        failed_tasks = total_tasks - scheduled_tasks

        teacher_gaps = self._calc_teacher_gaps(records)
        main_morning_rate = self._calc_main_morning_rate(records)
        continuous_rate = self._calc_continuous_rate(records)

        score = self._calc_score(
            records, total_tasks, teacher_gaps,
            main_morning_rate, continuous_rate,
        )

        return {
            "schedule_id": schedule_id,
            "score": score,
            "total_tasks": total_tasks,
            "scheduled_tasks": scheduled_tasks,
            "failed_tasks": failed_tasks,
            "total_periods": len(records),
            "teacher_gaps": teacher_gaps,
            "main_morning_rate": round(main_morning_rate, 1),
            "continuous_rate": round(continuous_rate, 1),
        }

    def _calc_score(
        self, records, total_tasks, teacher_gaps,
        main_morning_rate, continuous_rate,
    ) -> int:
        score = 0.0
        scheduled_ids = {r.task_id for r in records}
        if total_tasks > 0:
            score += (len(scheduled_ids) / total_tasks) * 40
        score += (main_morning_rate / 100) * 20

        if teacher_gaps == 0:
            score += 20
        elif teacher_gaps < 5:
            score += 16
        elif teacher_gaps < 10:
            score += 12
        elif teacher_gaps < 20:
            score += 8
        elif teacher_gaps < 40:
            score += 4

        score += (continuous_rate / 100) * 20
        return min(int(score), 100)

    def _calc_teacher_gaps(self, records: List[ScheduleRecord]) -> int:
        td: Dict[tuple, List[int]] = defaultdict(list)
        for r in records:
            td[(r.teacher_id, r.day)].append(r.period)
        total = 0
        for _, periods in td.items():
            if len(periods) < 2:
                continue
            sp = sorted(set(periods))
            for i in range(len(sp) - 1):
                gap = sp[i + 1] - sp[i] - 1
                if gap > 0:
                    total += gap
        return total

    def _calc_main_morning_rate(self, records: List[ScheduleRecord]) -> float:
        mt, mm = 0, 0
        for r in records:
            subj = self.data.get_subject(r.subject_id)
            if subj and subj.is_main:
                mt += 1
                if r.period <= 5:
                    mm += 1
        return (mm / mt * 100) if mt > 0 else 100.0

    def _calc_continuous_rate(self, records: List[ScheduleRecord]) -> float:
        cont_tasks = [
            t for t in self.data.tasks
            if t.is_continuous and t.continuous_count > 1
        ]
        if not cont_tasks:
            return 100.0

        task_day: Dict[tuple, List[int]] = defaultdict(list)
        for r in records:
            task_day[(r.task_id, r.day)].append(r.period)

        complete = 0
        for task in cont_tasks:
            found = False
            for day in range(1, 6):
                periods = sorted(task_day.get((task.id, day), []))
                cc = task.continuous_count
                if len(periods) >= cc:
                    for i in range(len(periods) - cc + 1):
                        if periods[i + cc - 1] - periods[i] == cc - 1:
                            found = True
                            break
                if found:
                    break
            if found:
                complete += 1
        return (complete / len(cont_tasks)) * 100
