"""
========================================
选课数据库模型
========================================

管理学生 A-Level 选课记录。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class CourseSelection(Base):
    """
    选课数据模型
    
    对应数据库中的 course_selections 表，存储学生的选课记录。
    """
    __tablename__ = "course_selections"
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="选课记录ID，主键"
    )
    
    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        comment="学生ID"
    )
    
    academic_year = Column(
        String(20),
        nullable=False,
        default="2025-2026",
        comment="学年"
    )
    
    semester = Column(
        String(10),
        nullable=False,
        default="FALL",
        comment="学期：FALL/SPRING"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="APPROVED",
        comment="状态（保留字段，新建默认已批准，供自动分班等流程筛选）"
    )
    
    selections = Column(
        JSON,
        default=list,
        comment="选课列表 [{alevel_subject_id, priority}]"
    )
    
    total_weekly_hours = Column(
        Integer,
        default=0,
        comment="总周课时"
    )
    
    note = Column(
        String(500),
        nullable=True,
        comment="备注"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )
    
    is_deleted = Column(
        Boolean,
        default=False,
        comment="是否已删除（软删除）"
    )
    
    def __repr__(self) -> str:
        return f"<CourseSelection(id={self.id}, student_id={self.student_id}, status='{self.status}')>"
