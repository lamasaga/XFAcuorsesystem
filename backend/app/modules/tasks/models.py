"""
========================================
教学任务数据库模型
========================================

教学任务表示"某教师教某班级某科目"的关系。
这是排课系统的核心数据，排课算法就是为这些任务分配时间槽。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class TeachingTask(Base):
    """
    教学任务数据模型
    
    表示一个教学任务：某教师教某班级某科目。
    
    Attributes:
        id: 任务 ID
        teacher_id: 教师 ID（外键）
        class_id: 班级 ID（外键）
        subject_id: 科目 ID（外键）
        weekly_hours: 周课时数
        is_continuous: 是否需要连堂
        continuous_count: 连堂节数
    """
    
    __tablename__ = "teaching_tasks"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="任务ID")
    
    # 外键关联
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False, comment="教师ID")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, comment="班级ID")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, comment="科目ID")
    
    # 课时信息
    weekly_hours = Column(Integer, nullable=False, default=2, comment="周课时数")
    
    # 连堂设置
    is_continuous = Column(Boolean, default=False, comment="是否需要连堂")
    continuous_count = Column(Integer, default=2, comment="连堂节数")
    
    # 关联的分层组ID (如果是分层课，此字段不为空)
    layer_group_id = Column(Integer, ForeignKey("layer_groups.id"), nullable=True, comment="关联的分层组ID")
    
    # 优先时段
    preferred_period = Column(String(20), nullable=True, comment="优先时段：MORNING/AFTERNOON")
    
    # 备注
    note = Column(String(200), nullable=True, comment="备注")
    
    # 系统字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    # 关系定义（用于 ORM 查询时自动加载关联数据）
    # 注意：这些关系需要对应的模型已导入
    # teacher = relationship("Teacher", back_populates="tasks")
    # class_ = relationship("Class", back_populates="tasks")
    # subject = relationship("Subject", back_populates="tasks")
    
    def __repr__(self) -> str:
        return f"<TeachingTask(id={self.id}, teacher={self.teacher_id}, class={self.class_id}, subject={self.subject_id})>"
