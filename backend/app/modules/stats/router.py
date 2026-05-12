"""
统计 API 模块

提供 Dashboard 和其他页面所需的统计数据。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.dependencies import get_db
from ..teachers.models import Teacher
from ..classes.models import Class
from ..subjects.models import Subject
from ..tasks.models import TeachingTask
from ..schedules.models import Schedule, ScheduleItem
from ..layers.models import LayerGroup
from ..venues.models import Venue

router = APIRouter(
    tags=["统计数据 (Statistics)"]
)


@router.get("/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    """
    获取系统概览统计
    
    返回：教师数、班级数、科目数、教学任务数、已排课数等
    """
    # 基础数据统计
    teacher_count = db.query(func.count(Teacher.id)).filter(Teacher.is_deleted == False).scalar() or 0
    class_count = db.query(func.count(Class.id)).filter(Class.is_deleted == False).scalar() or 0
    subject_count = db.query(func.count(Subject.id)).filter(Subject.is_deleted == False).scalar() or 0
    task_count = db.query(func.count(TeachingTask.id)).filter(TeachingTask.is_deleted == False).scalar() or 0
    
    # 排课统计
    schedule_count = db.query(func.count(Schedule.id)).scalar() or 0
    active_schedule = db.query(Schedule).filter(Schedule.is_active == True).first()
    
    # 如果有激活的课表，计算已排课时
    scheduled_periods = 0
    if active_schedule:
        scheduled_periods = db.query(func.count(ScheduleItem.id)).filter(
            ScheduleItem.schedule_id == active_schedule.id
        ).scalar() or 0
    
    # 计算总周课时需求
    total_weekly_hours = db.query(func.sum(TeachingTask.weekly_hours)).filter(
        TeachingTask.is_deleted == False
    ).scalar() or 0
    
    # 分层组和场地统计
    layer_group_count = db.query(func.count(LayerGroup.id)).scalar() or 0
    venue_count = db.query(func.count(Venue.id)).scalar() or 0
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "teacher_count": teacher_count,
            "class_count": class_count,
            "subject_count": subject_count,
            "task_count": task_count,
            "schedule_count": schedule_count,
            "active_schedule_id": active_schedule.id if active_schedule else None,
            "scheduled_periods": scheduled_periods,
            "total_weekly_hours": total_weekly_hours,
            "layer_group_count": layer_group_count,
            "venue_count": venue_count,
            # 排课状态
            "schedule_status": {
                "has_schedule": schedule_count > 0,
                "has_active": active_schedule is not None,
                "completion_rate": round(scheduled_periods / total_weekly_hours * 100, 1) if total_weekly_hours > 0 else 0
            }
        }
    }


@router.get("/data-check")
def check_data_readiness(db: Session = Depends(get_db)):
    """
    检查排课数据准备状态
    
    用于自动排课前的数据验证。
    """
    checks = []
    all_passed = True
    
    # 1. 检查教师数据
    teacher_count = db.query(func.count(Teacher.id)).filter(Teacher.is_deleted == False).scalar() or 0
    checks.append({
        "key": "teacher",
        "title": "教师数据",
        "detail": f"已录入 {teacher_count} 位教师" if teacher_count > 0 else "未录入教师信息",
        "status": "success" if teacher_count > 0 else "error"
    })
    if teacher_count == 0:
        all_passed = False
    
    # 2. 检查班级数据
    class_count = db.query(func.count(Class.id)).filter(Class.is_deleted == False).scalar() or 0
    checks.append({
        "key": "class",
        "title": "班级数据",
        "detail": f"已录入 {class_count} 个班级" if class_count > 0 else "未录入班级信息",
        "status": "success" if class_count > 0 else "error"
    })
    if class_count == 0:
        all_passed = False
    
    # 3. 检查科目数据
    subject_count = db.query(func.count(Subject.id)).filter(Subject.is_deleted == False).scalar() or 0
    checks.append({
        "key": "subject",
        "title": "科目数据",
        "detail": f"已配置 {subject_count} 门科目" if subject_count > 0 else "未配置科目",
        "status": "success" if subject_count > 0 else "error"
    })
    if subject_count == 0:
        all_passed = False
    
    # 4. 检查教学任务
    task_count = db.query(func.count(TeachingTask.id)).filter(TeachingTask.is_deleted == False).scalar() or 0
    checks.append({
        "key": "task",
        "title": "教学任务",
        "detail": f"已配置 {task_count} 个教学任务" if task_count > 0 else "未配置教学任务",
        "status": "success" if task_count > 0 else "error"
    })
    if task_count == 0:
        all_passed = False
    
    # 5. 检查场地配置（可选，给警告）
    venue_count = db.query(func.count(Venue.id)).scalar() or 0
    checks.append({
        "key": "venue",
        "title": "场地配置",
        "detail": f"已配置 {venue_count} 个场地" if venue_count > 0 else "未配置场地（可选）",
        "status": "success" if venue_count > 0 else "warning"
    })
    
    # 6. 检查分层课程（可选，给警告）
    layer_count = db.query(func.count(LayerGroup.id)).scalar() or 0
    checks.append({
        "key": "layer",
        "title": "分层课程",
        "detail": f"已配置 {layer_count} 门分层课程" if layer_count > 0 else "未配置分层课程（可选）",
        "status": "success" if layer_count > 0 else "warning"
    })
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "checks": checks,
            "all_passed": all_passed,
            "can_schedule": all_passed  # 只有必填项都通过才能排课
        }
    }


@router.get("/schedule-stats/{schedule_id}")
def get_schedule_stats(schedule_id: int, db: Session = Depends(get_db)):
    """
    获取指定课表的统计信息
    """
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        return {"code": 404, "message": "课表不存在", "data": None}
    
    # 统计总课时
    total_periods = db.query(func.count(ScheduleItem.id)).filter(
        ScheduleItem.schedule_id == schedule_id
    ).scalar() or 0
    
    # 按教师统计
    teacher_stats = db.query(
        ScheduleItem.teacher_id,
        func.count(ScheduleItem.id).label('period_count')
    ).filter(
        ScheduleItem.schedule_id == schedule_id
    ).group_by(ScheduleItem.teacher_id).all()
    
    # 按班级统计
    class_stats = db.query(
        ScheduleItem.class_id,
        func.count(ScheduleItem.id).label('period_count')
    ).filter(
        ScheduleItem.schedule_id == schedule_id
    ).group_by(ScheduleItem.class_id).all()
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "schedule_id": schedule_id,
            "schedule_name": schedule.name,
            "is_active": schedule.is_active,
            "total_periods": total_periods,
            "teacher_count": len(teacher_stats),
            "class_count": len(class_stats)
        }
    }
