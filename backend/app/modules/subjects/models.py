"""
========================================
科目数据库模型
========================================
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.compat import PortableArray


class Subject(Base):
    """
    科目数据模型
    
    Attributes:
        id: 科目 ID
        code: 科目代码（唯一）
        name: 科目名称
        category: 科目分类（文化课/艺术/体育/综合）
        is_main: 是否为主科（语数英）
        required_room_type: 所需教室类型
        color: 显示颜色
        applicable_grades: 适用年级列表
        applicable_class_types: 适用班型列表
    """
    
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="科目ID")
    code = Column(String(20), unique=True, nullable=False, comment="科目代码")
    name = Column(String(50), nullable=False, comment="科目名称")
    category = Column(String(20), default="文化课", comment="分类：文化课/艺术/体育/综合")
    is_main = Column(Boolean, default=False, comment="是否主科")
    required_room_type = Column(String(30), nullable=True, comment="所需教室类型")
    color = Column(String(10), default="#3b82f6", comment="显示颜色")
    
    # 适用范围
    applicable_grades = Column(PortableArray(item_type="string"), default=[], comment="适用年级列表，如['G1','G2']")
    applicable_class_types = Column(PortableArray(item_type="string"), default=[], comment="适用班型，如['INTERNATIONAL','COMPREHENSIVE']")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    
    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, name='{self.name}')>"
