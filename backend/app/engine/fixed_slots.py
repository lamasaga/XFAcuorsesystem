"""
固定课表时段（不参与自动排课，生成方案时直接写入并锁定）。

当前规则：每周五下午最后一节（第 8 节）为班会。
"""
from typing import List, Optional, Set, Tuple

from .data.models import ScheduleData, ScheduleRecord, Subject, Task, Class

# 周五 = 5，下午最后一节 = 8（与 friday_max_period 一致）
CLASS_MEETING_DAY = 5
CLASS_MEETING_PERIOD = 8
CLASS_MEETING_SLOT: Tuple[int, int] = (CLASS_MEETING_DAY, CLASS_MEETING_PERIOD)

_CLASS_MEETING_NAMES = frozenset({"班会", "班会课"})
_CLASS_MEETING_CODES = frozenset({"ASSEMBLY", "CLASS_MEETING"})


def is_class_meeting_subject(subject: Optional[Subject]) -> bool:
    if not subject:
        return False
    name = (subject.name or "").strip()
    code = (getattr(subject, "code", None) or "").strip().upper()
    return name in _CLASS_MEETING_NAMES or code in _CLASS_MEETING_CODES


def is_class_meeting_task(data: ScheduleData, task: Task) -> bool:
    if task.subject_name in _CLASS_MEETING_NAMES:
        return True
    return is_class_meeting_subject(data.get_subject(task.subject_id))


def find_class_meeting_subject(data: ScheduleData) -> Optional[Subject]:
    for subject in data.subjects:
        if is_class_meeting_subject(subject):
            return subject
    return None


def collect_homeroom_teacher_ids(data: ScheduleData) -> Set[int]:
    ids: Set[int] = set()
    for cls in data.classes:
        if cls.homeroom_cn_id:
            ids.add(cls.homeroom_cn_id)
        if cls.homeroom_en_id:
            ids.add(cls.homeroom_en_id)
    return ids


def find_class_meeting_task_for_class(
    data: ScheduleData, class_id: int, subject_id: Optional[int],
) -> Optional[Task]:
    for task in data.tasks:
        if task.class_id != class_id:
            continue
        if is_class_meeting_task(data, task):
            return task
    return None


def resolve_class_meeting_teacher(
    cls: Class, task: Optional[Task],
) -> Optional[int]:
    if cls.homeroom_cn_id:
        return cls.homeroom_cn_id
    if cls.homeroom_en_id:
        return cls.homeroom_en_id
    if task and task.teacher_id:
        return task.teacher_id
    return None


def class_has_meeting_task(data: ScheduleData, class_id: int) -> bool:
    return any(
        is_class_meeting_task(data, t)
        for t in data.tasks
        if t.class_id == class_id
    )


# 周五第 8 节固定班会后，求解器每周最多可排的行政班课时（9*4 + 7）
MAX_WEEKLY_SOLVER_PERIODS = 43


def compute_meeting_hour_trim_task_ids(data: ScheduleData) -> dict[int, int]:
    """
    为预留周五班会时段，当某班可排课时超过上限时，从普通课任务扣减课时。
    返回 {task_id: 扣减节数}。
    """
    trim: dict[int, int] = {}

    for cls in data.classes:
        candidates = [
            t for t in data.tasks
            if t.class_id == cls.id
            and not is_class_meeting_task(data, t)
            and not t.layer_group_id
        ]
        layer_hours = sum(
            t.weekly_hours for t in data.tasks
            if t.class_id == cls.id and t.layer_group_id
        )
        if not candidates and layer_hours <= MAX_WEEKLY_SOLVER_PERIODS:
            continue

        remaining = {t.id: t.weekly_hours for t in candidates}
        total = sum(remaining.values()) + layer_hours

        def pick_task_id() -> Optional[int]:
            pool = [tid for tid, h in remaining.items() if h > 0]
            if not pool:
                return None
            tasks = [t for t in candidates if t.id in pool]

            def sort_key(t: Task):
                subj = data.get_subject(t.subject_id)
                is_main = subj.is_main if subj else True
                return (is_main, remaining[t.id], t.id)

            return sorted(tasks, key=sort_key)[0].id

        while total > MAX_WEEKLY_SOLVER_PERIODS:
            tid = pick_task_id()
            if tid is None:
                break
            remaining[tid] -= 1
            trim[tid] = trim.get(tid, 0) + 1
            total -= 1

    trimmed_classes = len({t.class_id for t in data.tasks if t.id in trim})
    if trim:
        print(
            f"    [固定时段] {trimmed_classes} 个班可排课时超出 {MAX_WEEKLY_SOLVER_PERIODS}，"
            f"已扣减 {sum(trim.values())} 课时以预留周五班会"
        )
    return trim


def effective_task_weekly_hours(
    data: ScheduleData, task: Task, trim_task_ids: dict[int, int],
) -> int:
    hours = task.weekly_hours - trim_task_ids.get(task.id, 0)
    return max(0, hours)


def session_conflicts_class_meeting_slot(
    day: int, start_period: int, duration: int, class_ids: List[int],
) -> bool:
    """该 session 若排在此位置，是否会占用周五班会时段。"""
    if not class_ids or day != CLASS_MEETING_DAY:
        return False
    occupied = range(start_period, start_period + duration)
    return CLASS_MEETING_PERIOD in occupied


def build_fixed_class_meeting_records(data: ScheduleData) -> List[ScheduleRecord]:
    """为每个行政班生成锁定的班会课记录（周五第 8 节）。"""
    subject = find_class_meeting_subject(data)
    if not subject:
        print("    [固定时段] 未找到「班会」科目，跳过周五班会预置")
        return []

    records: List[ScheduleRecord] = []
    skipped = 0

    for cls in data.classes:
        task = find_class_meeting_task_for_class(data, cls.id, subject.id)
        teacher_id = resolve_class_meeting_teacher(cls, task)
        if not teacher_id:
            skipped += 1
            continue

        records.append(
            ScheduleRecord(
                task_id=task.id if task else 0,
                teacher_id=teacher_id,
                class_id=cls.id,
                subject_id=subject.id,
                day=CLASS_MEETING_DAY,
                period=CLASS_MEETING_PERIOD,
                duration=1,
                is_locked=True,
            )
        )

    print(
        f"    [固定时段] 周五第{CLASS_MEETING_PERIOD}节班会: "
        f"{len(records)} 个班已预置"
        + (f"，{skipped} 个班无班主任跳过" if skipped else "")
    )
    return records
