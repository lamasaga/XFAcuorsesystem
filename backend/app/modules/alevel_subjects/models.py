"""
========================================
A-Level 科目数据库模型
========================================

管理 A-Level 考试科目定义。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.core.database import Base


class AlevelSubject(Base):
    """
    A-Level 科目数据模型
    
    对应数据库中的 alevel_subjects 表，存储 A-Level 考试科目信息。
    """
    __tablename__ = "alevel_subjects"
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="科目ID，主键"
    )
    
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=True,
        comment="关联的基础科目ID"
    )
    
    exam_board = Column(
        String(20),
        nullable=False,
        default="CAIE",
        comment="考试局：CAIE/Edexcel/AQA"
    )
    
    level = Column(
        String(10),
        nullable=False,
        default="AS",
        comment="级别：AS/A2"
    )
    
    module_code = Column(
        String(30),
        nullable=True,
        comment="模块代码，如 9702/12"
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment="科目名称"
    )
    
    weekly_hours = Column(
        Integer,
        default=4,
        comment="每周课时"
    )
    
    max_students = Column(
        Integer,
        default=20,
        comment="最大学生人数"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        comment="是否启用"
    )
    
    description = Column(
        String(500),
        nullable=True,
        comment="科目描述"
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
    
    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id"),
        nullable=True,
        comment="默认授课教师ID"
    )
    
    is_deleted = Column(
        Boolean,
        default=False,
        comment="是否已删除（软删除）"
    )
    
    def __repr__(self) -> str:
        return f"<AlevelSubject(id={self.id}, name='{self.name}', exam_board='{self.exam_board}', level='{self.level}')>"
