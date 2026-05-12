"""
========================================
班级数据库模型
========================================

定义了班级表（classes）的结构。

班级命名规则：
- I类班级（国际班）：如 IG3-1（G3年级1班国际班）
- N类班级（综素班）：如 NG2-1（G2年级1班综素班）
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Class(Base):
    """
    班级数据模型
    
    对应数据库中的 classes 表。
    
    Attributes:
        id: 班级 ID
        name: 班级名称（如 IG3-1）
        type: 班级类型（I=国际班，N=综素班）
        grade: 年级（PK/KG/G1-G11）
        class_no: 班级序号
        department: 学部（PRIMARY/SECONDARY）
        homeroom_cn_id: 中教班主任 ID
        homeroom_en_id: 外教班主任 ID
    """
    
    __tablename__ = "classes"
    
    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="班级ID")
    
    # 基本信息
    name = Column(String(20), nullable=False, unique=True, comment="班级名称，如 IG3-1")
    
    # 班级类型
    # I = 国际班（International）
    # N = 综素班（Normal/综合素质）
    type = Column(String(1), nullable=False, default="I", comment="班级类型：I=国际班，N=综素班")
    
    # 年级
    # PK = 学前班，KG = 幼儿园，G1-G11 = 1-11年级
    grade = Column(String(10), nullable=False, comment="年级：PK/KG/G1-G11")
    
    # 班级序号
    class_no = Column(Integer, nullable=False, default=1, comment="班级序号")
    
    # 学部
    # PRIMARY = 小学部（PK-G5）
    # SECONDARY = 中学部（G6-G11）
    department = Column(String(20), nullable=False, default="PRIMARY", comment="学部")
    
    # 班主任关联（外键）
    # 中教班主任
    homeroom_cn_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, comment="中教班主任ID")
    
    # 外教班主任
    homeroom_en_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, comment="外教班主任ID")
    
    # 系统字段
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    is_deleted = Column(Boolean, default=False, comment="是否已删除")
    
    def __repr__(self) -> str:
        return f"<Class(id={self.id}, name='{self.name}', type='{self.type}')>"
