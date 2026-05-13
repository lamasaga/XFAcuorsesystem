"""
========================================
时间槽配置数据验证模式（Schemas）
========================================
"""

from pydantic import BaseModel
from typing import Optional
from datetime import time


class TimeSlotConfigResponse(BaseModel):
    """时间槽配置响应模式"""
    id: int
    department: str
    day_type: str
    period_num: int
    period_name: str
    start_time: str   # HH:MM 格式
    end_time: str     # HH:MM 格式
    period_type: str
    is_active: bool

    class Config:
        from_attributes = True


class TimeSlotListResponse(BaseModel):
    """时间槽列表响应"""
    department: str
    day_type: str
    slots: list[TimeSlotConfigResponse]
