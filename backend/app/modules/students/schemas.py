"""
========================================
学生数据验证模式
========================================

使用 Pydantic 定义学生相关的数据验证模式。
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StudentBase(BaseModel):
    """学生基础数据模式"""
    name: str = Field(..., min_length=1, max_length=50, description="学生姓名")
    student_no: str = Field(..., min_length=1, max_length=30, description="学号")
    grade: str = Field(default="G10", description="年级：G10-G12")
    class_id: Optional[int] = Field(default=None, description="所属行政班ID")
    status: str = Field(default="ACTIVE", description="状态：ACTIVE/INACTIVE/GRADUATED")


class StudentCreate(StudentBase):
    """创建学生请求模式"""
    pass


class StudentUpdate(BaseModel):
    """更新学生请求模式"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=50, description="学生姓名")
    student_no: Optional[str] = Field(default=None, min_length=1, max_length=30, description="学号")
    grade: Optional[str] = Field(default=None, description="年级：G10-G12")
    class_id: Optional[int] = Field(default=None, description="所属行政班ID")
    status: Optional[str] = Field(default=None, description="状态：ACTIVE/INACTIVE/GRADUATED")


class StudentResponse(StudentBase):
    """学生响应模式"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    """学生列表响应模式"""
    code: int = 200
    message: str = "success"
    data: dict


class StudentPromoteRequest(BaseModel):
    """一键升年级请求"""
    grades: Optional[List[str]] = Field(
        default=None,
        description="要升级的年级列表（如 ['G10']），不传则升级所有非毕业在读学生"
    )


class SimpleResponse(BaseModel):
    """简单操作响应模式"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
