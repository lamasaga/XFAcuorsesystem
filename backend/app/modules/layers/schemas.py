from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# 基础模型
class LayerGroupBase(BaseModel):
    """
    分层/合班课程基础模型
    
    group_type 决定课程类型：
    - LAYER: 分层课程，年级内所有班级参与，多个老师同时教
    - COMBINE: 合班上课，指定班级合并，一个老师教
    """
    group_type: Literal["LAYER", "COMBINE"] = Field(
        default="LAYER", 
        description="类型：LAYER=分层课程, COMBINE=合班上课"
    )
    subject_id: int = Field(..., description="科目ID")
    grades: List[str] = Field(
        default=[], 
        description="适用年级列表，如 ['G6', 'G7']，分层模式必填"
    )
    class_ids: List[int] = Field(
        default=[], 
        description="合班时指定的班级ID列表，合班模式必填"
    )
    layer_count: int = Field(
        default=1, 
        ge=1, 
        description="分层数量，分层模式使用；合班模式固定为1"
    )
    teacher_ids: List[int] = Field(
        default=[], 
        description="教师ID列表。分层：每层一个老师；合班：只有一个老师"
    )
    is_cross_grade: bool = Field(False, description="是否跨年级，仅分层模式使用")
    weekly_hours: int = Field(..., ge=1, description="周课时数")
    needs_continuous: bool = Field(False, description="是否需要连堂")
    description: Optional[str] = None


# 创建时的模型
class LayerGroupCreate(LayerGroupBase):
    pass


# 更新时的模型
class LayerGroupUpdate(BaseModel):
    group_type: Optional[Literal["LAYER", "COMBINE"]] = None
    subject_id: Optional[int] = None
    grades: Optional[List[str]] = None
    class_ids: Optional[List[int]] = None
    layer_count: Optional[int] = None
    teacher_ids: Optional[List[int]] = None
    is_cross_grade: Optional[bool] = None
    weekly_hours: Optional[int] = None
    needs_continuous: Optional[bool] = None
    description: Optional[str] = None


# 数据库返回的模型
class LayerGroupResponse(LayerGroupBase):
    id: int
    
    class Config:
        from_attributes = True
