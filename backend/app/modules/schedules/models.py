from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    UniqueConstraint, DateTime, JSON, func,
)
from app.core.database import Base


class Schedule(Base):
    """排课方案主表"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="未命名课表")
    is_active = Column(Boolean, default=False)
    batch_id = Column(String, nullable=True, index=True)
    score = Column(Integer, default=0)
    meeting_info = Column(JSON, nullable=True, default=None, comment="教研组组会时间 JSON")
    created_at = Column(DateTime, server_default=func.now())


class ScheduleItem(Base):
    """课表项：某节课的具体安排
    
    支持两种课程类型：
    - homeroom: 行政班课程（通过 task_id 关联 teaching_tasks）
    - alevel: A-Level 课程（通过 course_class_id 关联 course_classes）
    """
    __tablename__ = "schedule_items"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))

    # 课程类型：homeroom = 行政班课程, alevel = A-Level 课程
    item_type = Column(
        String(20),
        nullable=False,
        default="homeroom",
        comment="课程类型：homeroom=行政班课程, alevel=A-Level课程"
    )

    # 行政班课程关联
    task_id = Column(Integer, ForeignKey("teaching_tasks.id"), nullable=True)
    
    # A-Level 课程关联
    course_class_id = Column(
        Integer,
        ForeignKey("course_classes.id"),
        nullable=True,
        comment="A-Level 课程班ID"
    )
    
    day = Column(Integer, nullable=False)     # 1-5
    period = Column(Integer, nullable=False)  # 1-13
    duration = Column(Integer, default=1, comment="持续节数（连堂课 > 1）")

    # 冗余字段方便查询
    teacher_id = Column(Integer, nullable=True)
    class_id = Column(Integer, nullable=True)
    subject_id = Column(Integer, nullable=True)

    # 手动锁定：锁定后不可被调课/自动排课移动
    is_locked = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint(
            'schedule_id', 'class_id', 'day', 'period',
            name='uq_schedule_class_time',
        ),
    )


class ScheduleConfig(Base):
    """约束配置表：存储用户的约束偏好"""
    __tablename__ = "schedule_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="默认配置")
    is_active = Column(Boolean, default=True)
    config_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
