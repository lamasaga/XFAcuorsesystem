"""
========================================
时间槽配置 API 路由
========================================

API 接口列表：
- GET /api/v1/time-slots          获取时间槽列表（支持按学部、星期类型过滤）
- GET /api/v1/time-slots/departments  获取所有学部列表

用途：
1. 前端课表显示真实时间段
2. 教师不可用时间设置时标注时间段
3. 排课引擎调试和验证
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from .models import TimeSlotConfig
from .schemas import TimeSlotConfigResponse

router = APIRouter()


@router.get("/", response_model=List[TimeSlotConfigResponse])
def list_time_slots(
    department: Optional[str] = Query(None, description="学部过滤：PRIMARY/SECONDARY/SENIOR"),
    day_type: Optional[str] = Query(None, description="星期类型过滤：MONDAY/TUE_THU/FRIDAY/MON_THU"),
    db: Session = Depends(get_db)
):
    """
    获取时间槽配置列表
    
    支持按学部和星期类型过滤，返回按 period_num 排序的结果。
    
    示例：
        GET /api/v1/time-slots?department=PRIMARY&day_type=MONDAY
        GET /api/v1/time-slots?department=SENIOR
    """
    query = db.query(TimeSlotConfig).filter(TimeSlotConfig.is_active == True)
    
    if department:
        query = query.filter(TimeSlotConfig.department == department)
    if day_type:
        query = query.filter(TimeSlotConfig.day_type == day_type)
    
    slots = query.order_by(
        TimeSlotConfig.department,
        TimeSlotConfig.day_type,
        TimeSlotConfig.period_num
    ).all()
    
    # 将 time 对象格式化为 HH:MM 字符串
    result = []
    for s in slots:
        result.append(TimeSlotConfigResponse(
            id=s.id,
            department=s.department,
            day_type=s.day_type,
            period_num=s.period_num,
            period_name=s.period_name,
            start_time=s.start_time.strftime("%H:%M") if s.start_time else "",
            end_time=s.end_time.strftime("%H:%M") if s.end_time else "",
            period_type=s.period_type,
            is_active=s.is_active,
        ))
    
    return result


@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    """
    获取所有已配置的学部列表
    
    返回各学部及其支持的星期类型和节次范围。
    """
    from sqlalchemy import func
    
    rows = db.query(
        TimeSlotConfig.department,
        TimeSlotConfig.day_type,
        func.min(TimeSlotConfig.period_num).label("min_period"),
        func.max(TimeSlotConfig.period_num).label("max_period"),
        func.count(TimeSlotConfig.id).label("count"),
    ).filter(
        TimeSlotConfig.is_active == True
    ).group_by(
        TimeSlotConfig.department,
        TimeSlotConfig.day_type
    ).order_by(
        TimeSlotConfig.department,
        TimeSlotConfig.day_type
    ).all()
    
    departments = {}
    for dept, day_type, min_p, max_p, count in rows:
        if dept not in departments:
            departments[dept] = []
        departments[dept].append({
            "day_type": day_type,
            "min_period": min_p,
            "max_period": max_p,
            "period_count": count,
        })
    
    return departments
