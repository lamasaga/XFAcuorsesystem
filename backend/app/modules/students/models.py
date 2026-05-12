"""
========================================
学生数据库模型
========================================

管理 G10-G12 A-Level 学生信息。
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Student(Base):
    """
    学生数据模型
    
    对应数据库中的 students 表，存储 A-Level 学生信息。
    """
    __tablename__ = "students"
    
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
        comment="学生ID，主键"
    )
    
    name = Column(
        String(50),
        nullable=False,
        comment="学生姓名"
    )
    
    student_no = Column(
        String(30),
        nullable=False,
        unique=True,
        comment="学号"
    )
    
    grade = Column(
        String(10),
        nullable=False,
        default="G10",
        comment="年级：G10-G12"
    )
    
    class_id = Column(
        Integer,
        ForeignKey("classes.id"),
        nullable=True,
        comment="所属行政班ID"
    )
    
    status = Column(
        String(20),
        nullable=False,
        default="ACTIVE",
        comment="状态：ACTIVE=在读，INACTIVE=休学，GRADUATED=毕业"
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
        return f"<Student(id={self.id}, name='{self.name}', student_no='{self.student_no}', grade='{self.grade}')>"
