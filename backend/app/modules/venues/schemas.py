from pydantic import BaseModel, Field
from typing import List, Optional

# 基础模型
class VenueBase(BaseModel):
    name: str = Field(..., description="场地名称")
    capacity: int = Field(1, ge=1, description="容量")
    subjects: List[str] = Field(..., description="关联科目列表")
    applicable_grades: Optional[List[str]] = Field(None, description="适用年级列表")
    description: Optional[str] = None

# 创建时的模型
class VenueCreate(VenueBase):
    pass

# 更新时的模型
class VenueUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    subjects: Optional[List[str]] = None
    applicable_grades: Optional[List[str]] = None
    description: Optional[str] = None

# 数据库返回的模型
class VenueResponse(VenueBase):
    id: int
    
    class Config:
        from_attributes = True
