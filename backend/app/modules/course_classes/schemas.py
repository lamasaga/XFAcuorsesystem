"""
========================================
课程班数据验证模式
========================================

使用 Pydantic 定义课程班相关的数据验证模式。
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CourseClassBase(BaseModel):
    """课程班基础数据模式"""
    alevel_subject_id: int = Field(..., description="A-Level 科目ID")
    teacher_id: Optional[int] = Field(default=None, description="授课教师ID")
    name: str = Field(..., min_length=1, max_length=100, description="课程班名称")
    code: Optional[str] = Field(default=None, max_length=30, description="课程班代码")
    max_capacity: int = Field(default=20, ge=1, le=100, description="最大容量")
    current_enrollment: int = Field(default=0, ge=0, description="当前人数")
    semester: str = Field(default="FALL", description="学期：FALL/SPRING")
    academic_year: str = Field(default="2025-2026", description="学年")
    schedule_pattern: Optional[dict] = Field(default=None, description="上课时间模式")
    status: str = Field(default="ACTIVE", description="状态：ACTIVE/CLOSED/PENDING")


class CourseClassCreate(CourseClassBase):
    """创建课程班请求模式"""
    pass


class CourseClassUpdate(BaseModel):
    """更新课程班请求模式"""
    alevel_subject_id: Optional[int] = Field(default=None, description="A-Level 科目ID")
    teacher_id: Optional[int] = Field(default=None, description="授课教师ID")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="课程班名称")
    code: Optional[str] = Field(default=None, max_length=30, description="课程班代码")
    max_capacity: Optional[int] = Field(default=None, ge=1, le=100, description="最大容量")
    current_enrollment: Optional[int] = Field(default=None, ge=0, description="当前人数")
    semester: Optional[str] = Field(default=None, description="学期")
    academic_year: Optional[str] = Field(default=None, description="学年")
    schedule_pattern: Optional[dict] = Field(default=None, description="上课时间模式")
    status: Optional[str] = Field(default=None, description="状态")


class CourseClassResponse(CourseClassBase):
    """课程班响应模式"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CourseClassListResponse(BaseModel):
    """课程班列表响应模式"""
    code: int = 200
    message: str = "success"
    data: dict


class CourseClassMemberBase(BaseModel):
    """课程班成员基础数据模式"""
    course_class_id: int = Field(..., description="课程班ID")
    student_id: int = Field(..., description="学生ID")
    status: str = Field(default="ENROLLED", description="状态：ENROLLED/DROPPED")


class CourseClassMemberCreate(CourseClassMemberBase):
    """创建课程班成员请求模式"""
    pass


class CourseClassMemberResponse(CourseClassMemberBase):
    """课程班成员响应模式"""
    id: int
    enrolled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SimpleResponse(BaseModel):
    """简单操作响应模式"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
