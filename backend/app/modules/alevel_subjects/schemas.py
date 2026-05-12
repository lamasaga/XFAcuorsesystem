"""
========================================
A-Level 科目数据验证模式
========================================

使用 Pydantic 定义 A-Level 科目相关的数据验证模式。
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AlevelSubjectBase(BaseModel):
    """A-Level 科目基础数据模式"""
    subject_id: Optional[int] = Field(default=None, description="关联的基础科目ID")
    exam_board: str = Field(default="CAIE", description="考试局：CAIE/Edexcel/AQA")
    level: str = Field(default="AS", description="级别：AS/A2")
    module_code: Optional[str] = Field(default=None, max_length=30, description="模块代码")
    name: str = Field(..., min_length=1, max_length=100, description="科目名称")
    weekly_hours: int = Field(default=4, ge=1, le=20, description="每周课时")
    max_students: int = Field(default=20, ge=1, le=100, description="最大学生人数")
    is_active: bool = Field(default=True, description="是否启用")
    description: Optional[str] = Field(default=None, max_length=500, description="科目描述")


class AlevelSubjectCreate(AlevelSubjectBase):
    """创建 A-Level 科目请求模式"""
    pass


class AlevelSubjectUpdate(BaseModel):
    """更新 A-Level 科目请求模式"""
    subject_id: Optional[int] = Field(default=None, description="关联的基础科目ID")
    exam_board: Optional[str] = Field(default=None, description="考试局")
    level: Optional[str] = Field(default=None, description="级别")
    module_code: Optional[str] = Field(default=None, max_length=30, description="模块代码")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="科目名称")
    weekly_hours: Optional[int] = Field(default=None, ge=1, le=20, description="每周课时")
    max_students: Optional[int] = Field(default=None, ge=1, le=100, description="最大学生人数")
    is_active: Optional[bool] = Field(default=None, description="是否启用")
    description: Optional[str] = Field(default=None, max_length=500, description="科目描述")


class AlevelSubjectResponse(AlevelSubjectBase):
    """A-Level 科目响应模式"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlevelSubjectListResponse(BaseModel):
    """A-Level 科目列表响应模式"""
    code: int = 200
    message: str = "success"
    data: dict


class SimpleResponse(BaseModel):
    """简单操作响应模式"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
