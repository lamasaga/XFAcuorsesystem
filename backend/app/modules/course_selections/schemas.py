"""
========================================
选课数据验证模式
========================================

使用 Pydantic 定义选课相关的数据验证模式。
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SelectionItem(BaseModel):
    """单个选课项"""
    alevel_subject_id: int = Field(..., description="A-Level 科目ID")
    priority: int = Field(default=1, ge=1, le=10, description="优先级")


class CourseSelectionBase(BaseModel):
    """选课基础数据模式"""
    student_id: int = Field(..., description="学生ID")
    academic_year: str = Field(default="2025-2026", description="学年")
    semester: str = Field(default="FALL", description="学期：FALL/SPRING")
    status: str = Field(default="APPROVED", description="状态（默认已批准，无需审批流程）")
    selections: List[SelectionItem] = Field(default=[], description="选课列表")
    total_weekly_hours: int = Field(default=0, ge=0, le=50, description="总周课时")
    note: Optional[str] = Field(default=None, max_length=500, description="备注")


class CourseSelectionCreate(CourseSelectionBase):
    """创建选课请求模式"""
    pass


class CourseSelectionUpdate(BaseModel):
    """更新选课请求模式"""
    student_id: Optional[int] = Field(default=None, description="学生ID")
    academic_year: Optional[str] = Field(default=None, description="学年")
    semester: Optional[str] = Field(default=None, description="学期")
    selections: Optional[List[SelectionItem]] = Field(default=None, description="选课列表")
    total_weekly_hours: Optional[int] = Field(default=None, ge=0, le=50, description="总周课时")
    note: Optional[str] = Field(default=None, max_length=500, description="备注")


class CourseSelectionResponse(CourseSelectionBase):
    """选课响应模式"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CourseSelectionListResponse(BaseModel):
    """选课列表响应模式"""
    code: int = 200
    message: str = "success"
    data: dict


class SimpleResponse(BaseModel):
    """简单操作响应模式"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
