"""
========================================
时间槽配置初始化数据
========================================

数据来源: docs/各学部课程时间槽规范.md
整理日期: 2026-05-12

使用方法：
    from app.modules.time_slots.init_data import init_time_slot_configs
    init_time_slot_configs(db)

本脚本在应用启动时自动执行（如果表为空），也可手动调用。
"""

from datetime import time
from sqlalchemy.orm import Session

from .models import TimeSlotConfig


# =========================================
# 小学部 (PRIMARY) 时间槽数据
# =========================================
PRIMARY_SLOTS = [
    # ---- 周一 (MONDAY) ----
    ("PRIMARY", "MONDAY", 1, "第1节课", "08:40", "09:20", "class"),
    ("PRIMARY", "MONDAY", 2, "第2节课", "09:25", "10:05", "class"),
    ("PRIMARY", "MONDAY", 3, "第3节课", "10:15", "10:55", "class"),
    ("PRIMARY", "MONDAY", 4, "第4节课", "11:00", "11:40", "class"),
    ("PRIMARY", "MONDAY", 5, "第5节课", "12:35", "13:15", "class"),
    ("PRIMARY", "MONDAY", 6, "第6节课", "13:25", "14:05", "class"),
    ("PRIMARY", "MONDAY", 7, "第7节课", "14:10", "14:50", "class"),
    ("PRIMARY", "MONDAY", 8, "第8节课", "15:10", "15:50", "class"),
    # ---- 周二~周四 (TUE_THU) ----
    ("PRIMARY", "TUE_THU", 1, "第1节课", "08:20", "09:00", "class"),
    ("PRIMARY", "TUE_THU", 2, "第2节课", "09:05", "09:45", "class"),
    ("PRIMARY", "TUE_THU", 3, "第3节课", "10:15", "10:55", "class"),
    ("PRIMARY", "TUE_THU", 4, "第4节课", "11:00", "11:40", "class"),
    ("PRIMARY", "TUE_THU", 5, "第5节课", "12:35", "13:15", "class"),
    ("PRIMARY", "TUE_THU", 6, "第6节课", "13:25", "14:05", "class"),
    ("PRIMARY", "TUE_THU", 7, "第7节课", "14:10", "14:50", "class"),
    ("PRIMARY", "TUE_THU", 8, "第8节课", "15:10", "15:50", "class"),
    # ---- 周五 (FRIDAY) ----
    ("PRIMARY", "FRIDAY", 1, "第1节课", "08:20", "09:00", "class"),
    ("PRIMARY", "FRIDAY", 2, "第2节课", "09:05", "09:45", "class"),
    ("PRIMARY", "FRIDAY", 3, "第3节课", "10:15", "10:55", "class"),
    ("PRIMARY", "FRIDAY", 4, "第4节课", "11:00", "11:40", "class"),
    ("PRIMARY", "FRIDAY", 5, "第5节课", "12:35", "13:15", "class"),
    ("PRIMARY", "FRIDAY", 6, "第6节课", "13:25", "14:05", "class"),
    ("PRIMARY", "FRIDAY", 7, "第7节课", "14:10", "14:50", "class"),
    ("PRIMARY", "FRIDAY", 8, "第8节课", "15:00", "15:40", "class"),
]


# =========================================
# 中学部 (SECONDARY) 时间槽数据
# =========================================
SECONDARY_SLOTS = [
    # ---- 周一 (MONDAY) ----
    ("SECONDARY", "MONDAY", 1, "第1节课", "08:30", "09:10", "class"),
    ("SECONDARY", "MONDAY", 2, "第2节课", "09:15", "09:55", "class"),
    ("SECONDARY", "MONDAY", 3, "第3节课", "10:05", "10:45", "class"),
    ("SECONDARY", "MONDAY", 4, "第4节课", "10:50", "11:30", "class"),
    ("SECONDARY", "MONDAY", 5, "第5节课", "11:40", "12:20", "class"),
    ("SECONDARY", "MONDAY", 6, "第6节课", "13:15", "13:55", "class"),
    ("SECONDARY", "MONDAY", 7, "第7节课", "14:05", "14:45", "class"),
    ("SECONDARY", "MONDAY", 8, "第8节课", "15:00", "15:40", "class"),
    ("SECONDARY", "MONDAY", 9, "第9节课", "15:50", "16:30", "class"),
    # ---- 周二~周四 (TUE_THU) ----
    ("SECONDARY", "TUE_THU", 1, "第1节课", "08:10", "08:50", "class"),
    ("SECONDARY", "TUE_THU", 2, "第2节课", "08:55", "09:35", "class"),
    ("SECONDARY", "TUE_THU", 3, "第3节课", "10:05", "10:45", "class"),
    ("SECONDARY", "TUE_THU", 4, "第4节课", "10:50", "11:30", "class"),
    ("SECONDARY", "TUE_THU", 5, "第5节课", "11:40", "12:20", "class"),
    ("SECONDARY", "TUE_THU", 6, "第6节课", "13:15", "13:55", "class"),
    ("SECONDARY", "TUE_THU", 7, "第7节课", "14:05", "14:45", "class"),
    ("SECONDARY", "TUE_THU", 8, "第8节课", "15:00", "15:40", "class"),
    ("SECONDARY", "TUE_THU", 9, "第9节课", "15:50", "16:30", "class"),
    # ---- 周五 (FRIDAY) ----
    ("SECONDARY", "FRIDAY", 1, "第1节课", "08:10", "08:50", "class"),
    ("SECONDARY", "FRIDAY", 2, "第2节课", "08:55", "09:35", "class"),
    ("SECONDARY", "FRIDAY", 3, "第3节课", "10:05", "10:45", "class"),
    ("SECONDARY", "FRIDAY", 4, "第4节课", "10:50", "11:30", "class"),
    ("SECONDARY", "FRIDAY", 5, "第5节课", "11:40", "12:20", "class"),
    ("SECONDARY", "FRIDAY", 6, "第6节课", "13:15", "13:55", "class"),
    ("SECONDARY", "FRIDAY", 7, "第7节课", "14:05", "14:45", "class"),
    ("SECONDARY", "FRIDAY", 8, "第8节课", "15:00", "15:40", "class"),
]


# =========================================
# 高中部 (SENIOR) 时间槽数据
# =========================================
# 注意：高中部第1-9节与初中部(SECONDARY)完全一致
# 差异仅在于周一~四有额外的第10-13节（选修课+晚自习）
SENIOR_SLOTS = [
    # ---- 周一 (MONDAY) — 与初中部完全一致 ----
    ("SENIOR", "MONDAY", 1, "第1节课", "08:30", "09:10", "class"),
    ("SENIOR", "MONDAY", 2, "第2节课", "09:15", "09:55", "class"),
    ("SENIOR", "MONDAY", 3, "第3节课", "10:05", "10:45", "class"),
    ("SENIOR", "MONDAY", 4, "第4节课", "10:50", "11:30", "class"),
    ("SENIOR", "MONDAY", 5, "第5节课", "11:40", "12:20", "class"),
    ("SENIOR", "MONDAY", 6, "第6节课", "13:15", "13:55", "class"),
    ("SENIOR", "MONDAY", 7, "第7节课", "14:05", "14:45", "class"),
    ("SENIOR", "MONDAY", 8, "第8节课", "15:00", "15:40", "class"),
    ("SENIOR", "MONDAY", 9, "第9节课", "15:50", "16:30", "class"),
    ("SENIOR", "MONDAY", 10, "第10节课(选修课)", "16:40", "17:20", "elective"),
    ("SENIOR", "MONDAY", 11, "第11节课(选修课)", "17:20", "18:00", "elective"),
    ("SENIOR", "MONDAY", 12, "第12节课(晚自习)", "18:30", "19:30", "self_study"),
    ("SENIOR", "MONDAY", 13, "第13节课(晚自习)", "19:30", "20:30", "self_study"),
    # ---- 周二~周四 (TUE_THU) — 与初中部完全一致 ----
    ("SENIOR", "TUE_THU", 1, "第1节课", "08:10", "08:50", "class"),
    ("SENIOR", "TUE_THU", 2, "第2节课", "08:55", "09:35", "class"),
    ("SENIOR", "TUE_THU", 3, "第3节课", "10:05", "10:45", "class"),
    ("SENIOR", "TUE_THU", 4, "第4节课", "10:50", "11:30", "class"),
    ("SENIOR", "TUE_THU", 5, "第5节课", "11:40", "12:20", "class"),
    ("SENIOR", "TUE_THU", 6, "第6节课", "13:15", "13:55", "class"),
    ("SENIOR", "TUE_THU", 7, "第7节课", "14:05", "14:45", "class"),
    ("SENIOR", "TUE_THU", 8, "第8节课", "15:00", "15:40", "class"),
    ("SENIOR", "TUE_THU", 9, "第9节课", "15:50", "16:30", "class"),
    ("SENIOR", "TUE_THU", 10, "第10节课(选修课)", "16:40", "17:20", "elective"),
    ("SENIOR", "TUE_THU", 11, "第11节课(选修课)", "17:20", "18:00", "elective"),
    ("SENIOR", "TUE_THU", 12, "第12节课(晚自习)", "18:30", "19:30", "self_study"),
    ("SENIOR", "TUE_THU", 13, "第13节课(晚自习)", "19:30", "20:30", "self_study"),
    # ---- 周五 (FRIDAY) — 与初中部完全一致，无第9-13节 ----
    ("SENIOR", "FRIDAY", 1, "第1节课", "08:10", "08:50", "class"),
    ("SENIOR", "FRIDAY", 2, "第2节课", "08:55", "09:35", "class"),
    ("SENIOR", "FRIDAY", 3, "第3节课", "10:05", "10:45", "class"),
    ("SENIOR", "FRIDAY", 4, "第4节课", "10:50", "11:30", "class"),
    ("SENIOR", "FRIDAY", 5, "第5节课", "11:40", "12:20", "class"),
    ("SENIOR", "FRIDAY", 6, "第6节课", "13:15", "13:55", "class"),
    ("SENIOR", "FRIDAY", 7, "第7节课", "14:05", "14:45", "class"),
    ("SENIOR", "FRIDAY", 8, "第8节课", "15:00", "15:40", "class"),
]


# 所有时间槽合并
ALL_TIME_SLOTS = PRIMARY_SLOTS + SECONDARY_SLOTS + SENIOR_SLOTS


def _parse_time(time_str: str) -> time:
    """将 'HH:MM' 字符串转换为 time 对象"""
    hour, minute = map(int, time_str.split(":"))
    return time(hour=hour, minute=minute)


def init_time_slot_configs(db: Session) -> int:
    """
    初始化时间槽配置数据

    如果表已存在数据，则跳过（幂等操作）。

    Args:
        db: 数据库会话

    Returns:
        int: 插入的记录数
    """
    existing_count = db.query(TimeSlotConfig).count()
    if existing_count > 0:
        print(f"[时间槽] 表已存在 {existing_count} 条记录，跳过初始化")
        return 0

    inserted = 0
    for dept, day_type, period_num, period_name, start_str, end_str, period_type in ALL_TIME_SLOTS:
        slot = TimeSlotConfig(
            department=dept,
            day_type=day_type,
            period_num=period_num,
            period_name=period_name,
            start_time=_parse_time(start_str),
            end_time=_parse_time(end_str),
            period_type=period_type,
            is_active=True,
        )
        db.add(slot)
        inserted += 1

    db.commit()
    print(f"[时间槽] 成功初始化 {inserted} 条时间槽配置记录")
    return inserted
