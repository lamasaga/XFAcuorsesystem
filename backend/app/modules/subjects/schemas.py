"""
========================================
科目数据验证模式
========================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SubjectBase(BaseModel):
    """科目基础模式"""
    
    code: str = Field(..., min_length=1, max_length=20, description="科目代码", examples=["CHINESE"])
    name: str = Field(..., min_length=1, max_length=50, description="科目名称", examples=["语文"])
    category: str = Field(default="文化课", description="分类")
    is_main: bool = Field(default=False, description="是否主科")
    required_room_type: Optional[str] = Field(None, description="所需教室类型")
    color: str = Field(default="#3b82f6", description="显示颜色")
    applicable_grades: List[str] = Field(default=[], description="适用年级列表，如['G1','G2']")
    applicable_class_types: List[str] = Field(default=[], description="适用班型，如['INTERNATIONAL','COMPREHENSIVE']")


class SubjectCreate(SubjectBase):
    """创建科目模式"""
    pass


class SubjectUpdate(BaseModel):
    """更新科目模式"""
    
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    category: Optional[str] = None
    is_main: Optional[bool] = None
    required_room_type: Optional[str] = None
    color: Optional[str] = None
    applicable_grades: Optional[List[str]] = None
    applicable_class_types: Optional[List[str]] = None


class SubjectResponse(SubjectBase):
    """科目响应模式"""
    
    id: int
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
