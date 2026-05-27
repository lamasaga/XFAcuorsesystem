"""
课表约束验证器 (v2)
对已生成的课表进行约束违反检测，返回每个 (day, period) 的违反列表。

核心改进：
- 每条违反记录携带 related_class_ids，过滤时按班级精准匹配
- 分层同步：正确检测「同一时间段内是否所有班级都参与」
- 软约束阈值合理化
"""

from collections import defaultdict
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session

from app.modules.schedules.models import ScheduleItem
from app.modules.subjects.models import Subject
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class
from app.modules.tasks.models import TeachingTask
from app.modules.venues.models import Venue


_ART_PE_KEYWORDS = {
    '体育', '美术', '音乐', '声乐', '钢琴', '轮滑',
    '舞蹈', '艺术', 'PE', 'Art', 'Music',
}


class ScheduleValidator:
    """课表状态验证器"""

    def __init__(
        self, db: Session, schedule_id: int,
        class_id: Optional[int] = None,
    ):
        self.db = db
        self.schedule_id = schedule_id
        self.filter_class_id = class_id
        self._load()

    def _load(self):
        """一次性加载课表及关联数据"""
        self.all_items: List[ScheduleItem] = self.db.query(
            ScheduleItem
        ).filter(
            ScheduleItem.schedule_id == self.schedule_id
        ).all()

        subject_ids = {i.subject_id for i in self.all_items if i.subject_id}
        teacher_ids = {i.teacher_id for i in self.all_items if i.teacher_id}
        class_ids = {i.class_id for i in self.all_items if i.class_id}
        task_ids = {i.task_id for i in self.all_items if i.task_id}

        self.subjects: Dict[int, Subject] = {
            s.id: s for s in self.db.query(Subject).filter(
                Subject.id.in_(subject_ids)).all()
        } if subject_ids else {}

        self.teachers: Dict[int, str] = {
            t.id: t.name for t in self.db.query(Teacher).filter(
                Teacher.id.in_(teacher_ids)).all()
        } if teacher_ids else {}

        self.classes: Dict[int, str] = {
            c.id: c.name for c in self.db.query(Class).filter(
                Class.id.in_(class_ids)).all()
        } if class_ids else {}

        self.tasks: Dict[int, TeachingTask] = {
            t.id: t for t in self.db.query(TeachingTask).filter(
                TeachingTask.id.in_(task_ids)).all()
        } if task_ids else {}

        # 场地: 科目名 → 可同时容纳的场地数
        venues = self.db.query(Venue).all()
        self.venue_capacities: Dict[str, int] = {}
        for v in venues:
            for sn in (v.subjects or []):
                self.venue_capacities[sn] = (
                    self.venue_capacities.get(sn, 0) + 1)

    # ----------------------------------------------------------
    #  公共接口
    # ----------------------------------------------------------

    def validate(self) -> dict:
        # 收集所有违反，每条携带 related_class_ids
        raw: Dict[str, list] = defaultdict(list)

        self._check_teacher_conflicts(raw)
        self._check_class_conflicts(raw)
        self._check_layer_sync(raw)
        self._check_venue_capacity(raw)
        self._check_daily_subject_limit(raw)
        self._check_soft_violations(raw)

        # 按班级过滤：只保留与目标班级相关的违反
        if self.filter_class_id:
            filtered: Dict[str, list] = defaultdict(list)
            for key, entries in raw.items():
                for e in entries:
                    cids = e.get("_class_ids")
                    if cids is None or self.filter_class_id in cids:
                        # 移除内部字段再返回
                        clean = {k: v for k, v in e.items()
                                 if not k.startswith("_")}
                        filtered[key].append(clean)
            violations = dict(filtered)
        else:
            violations = {}
            for key, entries in raw.items():
                violations[key] = [
                    {k: v for k, v in e.items() if not k.startswith("_")}
                    for e in entries
                ]

        hard_count = sum(
            1 for vl in violations.values()
            for v in vl if v["severity"] == "hard"
        )
        soft_count = sum(
            1 for vl in violations.values()
            for v in vl if v["severity"] == "soft"
        )
        # 评分：100 分基础，硬约束 -5/条，软约束 -1/条
        score = max(0, 100 - hard_count * 5 - soft_count)

        return {
            "violations": violations,
            "summary": {
                "hard_count": hard_count,
                "soft_count": soft_count,
                "score": score,
            },
        }

    # ----------------------------------------------------------
    #  辅助: 添加违反记录
    # ----------------------------------------------------------

    def _add(self, violations: dict, key: str,
             vtype: str, tier: int, severity: str,
             message: str, class_ids: Optional[Set[int]] = None):
        """统一添加违反条目，携带 _class_ids 供过滤"""
        violations[key].append({
            "type": vtype,
            "tier": tier,
            "severity": severity,
            "message": message,
            "_class_ids": class_ids,  # 内部字段，输出前移除
        })

    # ----------------------------------------------------------
    #  Tier 1: 教师冲突
    # ----------------------------------------------------------

    def _check_teacher_conflicts(self, violations: dict):
        slots: Dict[tuple, list] = defaultdict(list)
        for it in self.all_items:
            if it.teacher_id:
                slots[(it.teacher_id, it.day, it.period)].append(it)

        for (tid, d, p), items in slots.items():
            if len(items) <= 1:
                continue
            tname = self.teachers.get(tid, f"T{tid}")
            involved_cids = {i.class_id for i in items if i.class_id}
            details = []
            for i in items:
                cn = self.classes.get(i.class_id, "")
                sn = self.subjects[i.subject_id].name if i.subject_id in self.subjects else ""
                details.append(f"{cn}{sn}")
            msg = f"教师 {tname} 时间冲突（{', '.join(details)}）"
            self._add(violations, f"{d}-{p}",
                      "teacher_conflict", 1, "hard", msg, involved_cids)

    # ----------------------------------------------------------
    #  Tier 1: 班级冲突
    # ----------------------------------------------------------

    def _check_class_conflicts(self, violations: dict):
        slots: Dict[tuple, list] = defaultdict(list)
        for it in self.all_items:
            if it.class_id:
                slots[(it.class_id, it.day, it.period)].append(it)

        for (cid, d, p), items in slots.items():
            if len(items) <= 1:
                continue
            # 同一分层组在同一时段的多条记录（如单班分层多教师）不算冲突
            layer_gids = set()
            for it in items:
                task = self.tasks.get(it.task_id) if it.task_id else None
                if not task or not task.layer_group_id:
                    break
                layer_gids.add(task.layer_group_id)
            else:
                if len(layer_gids) == 1:
                    continue
            cn = self.classes.get(cid, f"C{cid}")
            subjs = [self.subjects[i.subject_id].name
                     if i.subject_id in self.subjects else ""
                     for i in items]
            self._add(violations, f"{d}-{p}",
                      "class_conflict", 1, "hard",
                      f"班级 {cn} 此时段排了 {len(items)} 节课（{', '.join(subjs)}）",
                      {cid})

    # ----------------------------------------------------------
    #  Tier 1: 分层组同步
    #
    #  正确逻辑: 分层组每周有 N 节课，会分布在 N 个不同时间段。
    #  在每个时间段，同组所有班级必须都参与。
    #  如果某个时间段只有部分班级，说明不同步。
    # ----------------------------------------------------------

    def _check_layer_sync(self, violations: dict):
        # 收集每个分层组的信息
        group_data: Dict[int, Dict] = defaultdict(lambda: {
            "all_class_ids": set(),
            "slot_classes": defaultdict(set),   # (d,p) -> set of class_id
            "slot_items": defaultdict(list),     # (d,p) -> [item, ...]
        })

        for it in self.all_items:
            task = self.tasks.get(it.task_id) if it.task_id else None
            if not task or not task.layer_group_id:
                continue
            gid = task.layer_group_id
            group_data[gid]["all_class_ids"].add(it.class_id)
            group_data[gid]["slot_classes"][(it.day, it.period)].add(
                it.class_id)
            group_data[gid]["slot_items"][(it.day, it.period)].append(it)

        for gid, info in group_data.items():
            all_cids = info["all_class_ids"]
            if len(all_cids) <= 1:
                continue

            for (d, p), present_cids in info["slot_classes"].items():
                if present_cids >= all_cids:
                    continue  # 所有班级都在此时段 → 同步正常

                # 部分班级缺席此时段 → 不同步
                missing_cids = all_cids - present_cids
                missing_names = sorted(
                    self.classes.get(c, f"C{c}") for c in missing_cids)

                # 只标记在此时段「有课但不全」的情况
                self._add(
                    violations, f"{d}-{p}",
                    "layer_desync", 1, "hard",
                    f"分层组#{gid} 不同步：{', '.join(missing_names)} "
                    f"未在此时段上课",
                    present_cids,  # 只关联在场的班级
                )

    # ----------------------------------------------------------
    #  Tier 1: 场地容量
    # ----------------------------------------------------------

    def _check_venue_capacity(self, violations: dict):
        type_slots: Dict[str, Dict[tuple, list]] = defaultdict(
            lambda: defaultdict(list))
        for it in self.all_items:
            subj = self.subjects.get(it.subject_id)
            if subj and subj.required_room_type:
                type_slots[subj.required_room_type][
                    (it.day, it.period)].append(it)

        for vtype, slot_map in type_slots.items():
            cap = self.venue_capacities.get(vtype, 999)
            for (d, p), items in slot_map.items():
                if len(items) <= cap:
                    continue
                involved = {i.class_id for i in items if i.class_id}
                self._add(
                    violations, f"{d}-{p}",
                    "venue_overcapacity", 1, "hard",
                    f"场地「{vtype}」此时段 {len(items)} 节课（容量 {cap}）",
                    involved,
                )

    # ----------------------------------------------------------
    #  硬约束: 同科目每日 ≤ 2 节（已从 Tier 2 升级为硬约束）
    # ----------------------------------------------------------

    def _check_daily_subject_limit(self, violations: dict):
        counter: Dict[tuple, list] = defaultdict(list)
        for it in self.all_items:
            if it.class_id and it.subject_id:
                counter[(it.class_id, it.subject_id, it.day)].append(it)

        for (cid, sid, d), items in counter.items():
            if len(items) <= 2:
                continue
            subj = self.subjects.get(sid)
            cn = self.classes.get(cid, "")
            sn = subj.name if subj else ""
            # 只标记一次（在第一节课的位置），而不是每节都标
            first_item = min(items, key=lambda x: x.period)
            self._add(
                violations, f"{d}-{first_item.period}",
                "daily_subject_exceed", 1, "hard",
                f"{cn} 的 {sn} 今天排了 {len(items)} 节（上限 2 节）",
                {cid},
            )

    # ----------------------------------------------------------
    #  Tier 3: 软约束
    # ----------------------------------------------------------

    def _check_soft_violations(self, violations: dict):
        for it in self.all_items:
            subj = self.subjects.get(it.subject_id)
            if not subj:
                continue
            cid = it.class_id
            key = f"{it.day}-{it.period}"

            # S1: 主科排在下午 (period >= 6)
            if subj.is_main and it.period >= 6:
                self._add(violations, key,
                          "main_not_morning", 3, "soft",
                          f"主科「{subj.name}」排在下午（建议上午）",
                          {cid} if cid else None)

            # S2: 艺体排第一节
            if subj.name in _ART_PE_KEYWORDS and it.period == 1:
                self._add(violations, key,
                          "artpe_first_period", 3, "soft",
                          f"「{subj.name}」排在第1节（建议避免）",
                          {cid} if cid else None)

        # S3: 科目分布不均 — 课时应尽可能分散到更多天
        #
        # 理想分布: N 节课应分散到 min(N, 5) 天
        #   - 1 节 → 1 天
        #   - 2 节 → 2 天
        #   - 3 节 → 3 天
        #   - 4 节 → 4 天
        #   - 5 节 → 5 天
        #   - 6 节 → 5 天 (有一天连堂)
        #   - 7+ 节 → 5 天
        # 允许偏差 1 天，即实际天数 < 理想天数 - 1 时才报警
        #
        # 例: 3 节课集中到 1 天 → 理想 3 天，实际 1 天，差 2 → 报警
        #     6 节课分布 4 天 → 理想 5 天，实际 4 天，差 1 → 不报警
        #     4 节课分布 2 天 → 理想 4 天，实际 2 天，差 2 → 报警

        # 统计每个 (class, subject) 的天分布和总课时
        cs_day_counts: Dict[tuple, Dict[int, int]] = defaultdict(
            lambda: defaultdict(int))
        for it in self.all_items:
            if it.class_id and it.subject_id:
                cs_day_counts[(it.class_id, it.subject_id)][it.day] += 1

        for (cid, sid), day_map in cs_day_counts.items():
            total_hours = sum(day_map.values())
            if total_hours <= 1:
                continue
            actual_days = len(day_map)
            ideal_days = min(total_hours, 5)

            if actual_days >= ideal_days - 1:
                continue  # 分布可接受

            subj = self.subjects.get(sid)
            cn = self.classes.get(cid, "")
            sn = subj.name if subj else ""

            # 找到课时最多的那天，在那天标记
            busiest_day = max(day_map, key=day_map.get)
            busiest_count = day_map[busiest_day]

            # 在最集中的那天的第一节课位置标记
            for it in self.all_items:
                if (it.class_id == cid and it.subject_id == sid
                        and it.day == busiest_day):
                    self._add(
                        violations, f"{it.day}-{it.period}",
                        "distribution_uneven", 3, "soft",
                        f"{cn} 的 {sn} 周{total_hours}节仅分布{actual_days}天"
                        f"（建议至少{ideal_days}天），"
                        f"周{busiest_day}排了{busiest_count}节过于集中",
                        {cid},
                    )
                    break  # 每个 (cid, sid) 只报一次
