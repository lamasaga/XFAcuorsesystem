from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal

LayerScopeType = Literal["GRADE", "CROSS_GRADE", "SINGLE_CLASS"]


def _normalize_layer_scope(
    layer_scope: Optional[str],
    is_cross_grade: Optional[bool],
) -> tuple[str, bool]:
    """统一 layer_scope 与 is_cross_grade。"""
    if layer_scope:
        scope = layer_scope
    elif is_cross_grade:
        scope = "CROSS_GRADE"
    else:
        scope = "GRADE"
    if scope not in ("GRADE", "CROSS_GRADE", "SINGLE_CLASS"):
        scope = "GRADE"
    return scope, scope == "CROSS_GRADE"


# 基础模型
class LayerGroupBase(BaseModel):
    """
    分层/合班课程基础模型
    
    group_type 决定课程类型：
    - LAYER: 分层课程，多个老师同时教
    - COMBINE: 合班上课，指定班级合并，一个老师教
    
    layer_scope（仅 LAYER）：
    - GRADE: 同年级多班参与
    - CROSS_GRADE: 跨年级混排
    - SINGLE_CLASS: 单一班级内分层
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
        description="涉及班级ID；合班/单班分层时由用户指定，同年级分层可自动推算"
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
    layer_scope: LayerScopeType = Field(
        default="GRADE",
        description="分层范围：GRADE/CROSS_GRADE/SINGLE_CLASS，仅 LAYER 使用",
    )
    is_cross_grade: bool = Field(
        False,
        description="是否跨年级（兼容字段，等价于 layer_scope=CROSS_GRADE）",
    )
    weekly_hours: int = Field(..., ge=1, description="周课时数")
    needs_continuous: bool = Field(False, description="是否需要连堂")
    description: Optional[str] = None

    @model_validator(mode="after")
    def sync_layer_scope_fields(self):
        scope, cross = _normalize_layer_scope(self.layer_scope, self.is_cross_grade)
        if self.group_type == "COMBINE":
            object.__setattr__(self, "layer_scope", "GRADE")
            object.__setattr__(self, "is_cross_grade", False)
        else:
            object.__setattr__(self, "layer_scope", scope)
            object.__setattr__(self, "is_cross_grade", cross)
        if self.layer_scope == "SINGLE_CLASS" and len(self.class_ids) > 1:
            raise ValueError("单一班级分层只能选择一个班级")
        if self.layer_scope == "SINGLE_CLASS" and self.layer_count < 2:
            raise ValueError("单一班级分层至少需要 2 层")
        return self


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
    layer_scope: Optional[LayerScopeType] = None
    is_cross_grade: Optional[bool] = None
    weekly_hours: Optional[int] = None
    needs_continuous: Optional[bool] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def sync_layer_scope_fields(self):
        if self.layer_scope is None and self.is_cross_grade is None:
            return self
        scope, cross = _normalize_layer_scope(self.layer_scope, self.is_cross_grade)
        if self.group_type != "COMBINE":
            object.__setattr__(self, "layer_scope", scope)
            object.__setattr__(self, "is_cross_grade", cross)
        return self


# 数据库返回的模型
class LayerGroupResponse(LayerGroupBase):
    id: int

    class Config:
        from_attributes = True
