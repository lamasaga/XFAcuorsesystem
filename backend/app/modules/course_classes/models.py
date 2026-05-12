"""
========================================
课程班数据库模型
========================================

管理 A-Level 课程班（按选课动态组成的教学班）。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class CourseClass(Base):
    """
    课程班数据模型
    
    对应数据库中的 course_classes 表，存储 A-Level 课程班信息。
    """
    __tablename__ = "course_classes"
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="课程班ID，主键"
    )
    
    alevel_subject_id = Column(
        Integer,
        ForeignKey("alevel_subjects.id"),
        nullable=False,
        comment="A-Level 科目ID"
    )
    
    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id"),
        nullable=True,
        comment="授课教师ID"
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment="课程班名称"
    )
    
    code = Column(
        String(30),
        nullable=True,
        comment="课程班代码"
    )
    
    max_capacity = Column(
        Integer,
        default=20,
        comment="最大容量"
    )
    
    current_enrollment = Column(
        Integer,
        default=0,
        comment="当前人数"
    )
    
    semester = Column(
        String(10),
        nullable=False,
        default="FALL",
        comment="学期：FALL/SPRING"
    )
    
    academic_year = Column(
        String(20),
        nullable=False,
        default="2025-2026",
        comment="学年"
    )
    
    schedule_pattern = Column(
        JSON,
        default=dict,
        comment="上课时间模式"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="ACTIVE",
        comment="状态：ACTIVE=活跃，CLOSED=已关闭，PENDING=待开课"
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
        return f"<CourseClass(id={self.id}, name='{self.name}', alevel_subject_id={self.alevel_subject_id})>"


class CourseClassMember(Base):
    """
    课程班成员数据模型
    
    对应数据库中的 course_class_members 表，存储课程班与学生关联。
    """
    __tablename__ = "course_class_members"
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="成员ID，主键"
    )
    
    course_class_id = Column(
        Integer,
        ForeignKey("course_classes.id"),
        nullable=False,
        comment="课程班ID"
    )
    
    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
        comment="学生ID"
    )
    
    enrolled_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="加入时间"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="ENROLLED",
        comment="状态：ENROLLED=已 enrollment，DROPPED=已退课"
    )
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间"
    )
    
    def __repr__(self) -> str:
        return f"<CourseClassMember(id={self.id}, course_class_id={self.course_class_id}, student_id={self.student_id})>"
