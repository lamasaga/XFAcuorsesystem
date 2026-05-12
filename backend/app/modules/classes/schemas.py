"""
========================================
班级数据验证模式
========================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClassBase(BaseModel):
    """班级基础模式"""
    
    name: str = Field(..., min_length=1, max_length=20, description="班级名称", examples=["IG3-1"])
    type: str = Field(default="I", description="班级类型：I=国际班，N=综素班")
    grade: str = Field(..., description="年级：PK/KG/G1-G11", examples=["G3"])
    class_no: int = Field(default=1, ge=1, le=10, description="班级序号")
    department: str = Field(default="PRIMARY", description="学部")
    homeroom_cn_id: Optional[int] = Field(None, description="中教班主任ID")
    homeroom_en_id: Optional[int] = Field(None, description="外教班主任ID")


class ClassCreate(ClassBase):
    """创建班级时使用的模式"""
    pass


class ClassUpdate(BaseModel):
    """更新班级时使用的模式"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=20)
    type: Optional[str] = None
    grade: Optional[str] = None
    class_no: Optional[int] = Field(None, ge=1, le=10)
    department: Optional[str] = None
    homeroom_cn_id: Optional[int] = None
    homeroom_en_id: Optional[int] = None


class ClassResponse(ClassBase):
    """班级响应模式"""
    
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
