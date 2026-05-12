"""
========================================
教学任务数据验证模式
========================================
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TeachingTaskBase(BaseModel):
    """教学任务基础模式"""
    
    teacher_id: int = Field(..., description="教师ID")
    class_id: int = Field(..., description="班级ID")
    subject_id: int = Field(..., description="科目ID")
    weekly_hours: int = Field(default=2, ge=1, le=10, description="周课时数")
    is_continuous: bool = Field(default=False, description="是否连堂")
    continuous_count: int = Field(default=2, ge=2, le=4, description="连堂节数")
    preferred_period: Optional[str] = Field(None, description="优先时段")
    note: Optional[str] = Field(None, max_length=200, description="备注")


class TeachingTaskCreate(TeachingTaskBase):
    """创建教学任务模式"""
    pass


class TeachingTaskUpdate(BaseModel):
    """更新教学任务模式"""
    
    teacher_id: Optional[int] = None
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    weekly_hours: Optional[int] = Field(None, ge=1, le=10)
    is_continuous: Optional[bool] = None
    continuous_count: Optional[int] = Field(None, ge=2, le=4)
    preferred_period: Optional[str] = None
    note: Optional[str] = Field(None, max_length=200)


class TeachingTaskResponse(TeachingTaskBase):
    """教学任务响应模式"""
    
    id: int
    created_at: Optional[datetime] = None
    
    # 关联数据（可选，用于返回完整信息）
    teacher_name: Optional[str] = None
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TeachingTaskWithDetails(BaseModel):
    """包含详细信息的教学任务响应"""
    
    id: int
    teacher_id: int
    class_id: int
    subject_id: int
    weekly_hours: int
    is_continuous: bool
    continuous_count: int
    preferred_period: Optional[str] = None
    note: Optional[str] = None
    
    # 关联信息
    teacher_name: str
    teacher_type: str
    class_name: str
    class_grade: str
    subject_name: str
    subject_code: str
    
    class Config:
        from_attributes = True
