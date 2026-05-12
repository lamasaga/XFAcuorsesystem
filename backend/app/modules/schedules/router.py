"""排课管理路由"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.dependencies import get_db
from app.engine.core import ScheduleEngine
from app.engine.solver import DEFAULT_SOFT_CONFIG
from . import models
from .schemas import ScheduleRequest, ScheduleConfigUpdate
from ..teachers.models import Teacher
from ..classes.models import Class
from ..subjects.models import Subject
from ..venues.models import Venue
from ..tasks.models import TeachingTask
from ..students.models import Student
from ..course_classes.models import CourseClass, CourseClassMember
from ..course_selections.models import CourseSelection
from ..alevel_subjects.models import AlevelSubject

router = APIRouter(tags=["排课管理 (Schedule Management)"])


# ===========================================================
#  排课生成
# ===========================================================

@router.post("/generate")
def generate_schedule(
    request: ScheduleRequest = None,
    db: Session = Depends(get_db),
):
    """触发自动排课"""
    if request is None:
        request = ScheduleRequest()

    print(f"[排课参数] scope={request.scope}, "
          f"optimization={request.optimization}, "
          f"plan_count={request.plan_count}")

    engine = ScheduleEngine(db)
    try:
        result = engine.run(
            optimization=request.optimization,
            plan_count=request.plan_count,
            scope=request.scope,
            grades=request.grades,
            class_ids=request.classes,
            keep_manual=request.keep_manual,
            debug=request.debug,
        )

        if isinstance(result, list):
            plans = [_format_plan(p, i) for i, p in enumerate(result)]
        else:
            plans = [_format_plan(result, 0)]

        return {
            "code": 200,
            "message": "排课成功",
            "data": {"plans": plans, "total_plans": len(plans)},
        }
    except RuntimeError as e:
        # 排课无解或数据冲突 — 返回 422 而非 500
        print(f"排课无解: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"排课出错: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _format_plan(plan: dict, index: int) -> dict:
    return {
        "schedule_id": plan.get("schedule_id"),
        "score": plan.get("score", 0),
        "total_tasks": plan.get("total_tasks", 0),
        "scheduled_tasks": plan.get("scheduled_tasks", 0),
        "failed_tasks": plan.get("failed_tasks", 0),
        "total_periods": plan.get("total_periods", 0),
        "teacher_gaps": plan.get("teacher_gaps", 0),
        "main_morning_rate": plan.get("main_morning_rate", 0),
        "continuous_rate": plan.get("continuous_rate", 0),
        "duration_seconds": plan.get("duration_seconds", 0),
        "recommended": index == 0,
    }


# ===========================================================
#  约束配置 API
# ===========================================================

@router.get("/config")
def get_schedule_config(db: Session = Depends(get_db)):
    """获取当前活跃的约束配置"""
    cfg = db.query(models.ScheduleConfig).filter(
        models.ScheduleConfig.is_active == True
    ).first()

    if cfg:
        return {
            "code": 200,
            "data": {
                "id": cfg.id,
                "name": cfg.name,
                "config": cfg.config_json,
            },
        }
    # 返回默认配置
    return {
        "code": 200,
        "data": {
            "id": None,
            "name": "默认配置",
            "config": {
                "soft_constraints": DEFAULT_SOFT_CONFIG,
                "meeting_slots": [],
            },
        },
    }


@router.put("/config")
def save_schedule_config(
    body: ScheduleConfigUpdate,
    db: Session = Depends(get_db),
):
    """保存约束配置"""
    config_data = body.config
    name = body.name or "自定义配置"

    # 将旧的活跃配置标为不活跃
    db.query(models.ScheduleConfig).filter(
        models.ScheduleConfig.is_active == True
    ).update({"is_active": False})

    cfg = models.ScheduleConfig(
        name=name,
        is_active=True,
        config_json=config_data,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)

    return {
        "code": 200,
        "message": "配置已保存",
        "data": {"id": cfg.id, "name": cfg.name},
    }


# ===========================================================
#  课表列表与详情
# ===========================================================

@router.get("/")
def get_schedules(db: Session = Depends(get_db)):
    """获取所有课表列表"""
    schedules = db.query(models.Schedule).order_by(
        desc(models.Schedule.id)
    ).all()
    return {
        "code": 200,
        "data": {
            "items": [
                {
                    "id": s.id,
                    "name": s.name,
                    "is_active": s.is_active,
                    "batch_id": s.batch_id,
                    "score": s.score,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in schedules
            ],
            "total": len(schedules),
        },
    }


@router.get("/{schedule_id}")
def get_schedule_detail(schedule_id: int, db: Session = Depends(get_db)):
    """获取指定课表详情"""
    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课表不存在")

    items = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id
    ).all()

    teacher_ids = {i.teacher_id for i in items if i.teacher_id}
    class_ids = {i.class_id for i in items if i.class_id}
    subject_ids = {i.subject_id for i in items if i.subject_id}

    teachers = {t.id: t.name for t in db.query(Teacher).filter(
        Teacher.id.in_(teacher_ids)).all()} if teacher_ids else {}
    classes = {c.id: c.name for c in db.query(Class).filter(
        Class.id.in_(class_ids)).all()} if class_ids else {}
    subjects = {s.id: s.name for s in db.query(Subject).filter(
        Subject.id.in_(subject_ids)).all()} if subject_ids else {}

    return {
        "code": 200,
        "data": {
            "id": schedule.id,
            "name": schedule.name,
            "is_active": schedule.is_active,
            "batch_id": schedule.batch_id,
            "score": schedule.score,
            "items": [
                {
                    "id": i.id,
                    "task_id": i.task_id,
                    "day": i.day,
                    "period": i.period,
                    "teacher_id": i.teacher_id,
                    "teacher_name": teachers.get(i.teacher_id, ""),
                    "class_id": i.class_id,
                    "class_name": classes.get(i.class_id, ""),
                    "subject_id": i.subject_id,
                    "subject_name": subjects.get(i.subject_id, ""),
                }
                for i in items
            ],
            "total_items": len(items),
        },
    }


@router.get("/{schedule_id}/by-class/{class_id}")
def get_class_timetable(
    schedule_id: int, class_id: int, db: Session = Depends(get_db),
):
    """获取指定班级的课表"""
    items = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.class_id == class_id,
    ).all()

    teacher_ids = {i.teacher_id for i in items if i.teacher_id}
    subject_ids = {i.subject_id for i in items if i.subject_id}

    teachers = {t.id: t.name for t in db.query(Teacher).filter(
        Teacher.id.in_(teacher_ids)).all()} if teacher_ids else {}
    subjects = {s.id: {"name": s.name, "color": s.color}
                for s in db.query(Subject).filter(
                    Subject.id.in_(subject_ids)).all()} if subject_ids else {}

    task_ids = {i.task_id for i in items if i.task_id}
    tasks_notes = {}
    if task_ids:
        tasks_notes = {t.id: t.note for t in db.query(TeachingTask).filter(
            TeachingTask.id.in_(task_ids)).all()}

    class_info = db.query(Class).filter(Class.id == class_id).first()

    timetable = {}
    for item in items:
        key = f"{item.day}-{item.period}"
        si = subjects.get(item.subject_id, {"name": "", "color": "#ccc"})
        timetable[key] = {
            "item_id": item.id,
            "subject_name": si["name"],
            "subject_color": si["color"],
            "teacher_name": teachers.get(item.teacher_id, ""),
            "note": tasks_notes.get(item.task_id, "") or "",
            "is_locked": bool(item.is_locked),
        }

    return {
        "code": 200,
        "data": {
            "class_id": class_id,
            "class_name": class_info.name if class_info else "",
            "timetable": timetable,
        },
    }


@router.get("/{schedule_id}/by-teacher/{teacher_id}")
def get_teacher_timetable(
    schedule_id: int, teacher_id: int, db: Session = Depends(get_db),
):
    """获取指定教师的课表"""
    items = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.teacher_id == teacher_id,
    ).all()

    class_ids = {i.class_id for i in items if i.class_id}
    subject_ids = {i.subject_id for i in items if i.subject_id}

    classes = {c.id: c.name for c in db.query(Class).filter(
        Class.id.in_(class_ids)).all()} if class_ids else {}
    subjects = {s.id: {"name": s.name, "color": s.color}
                for s in db.query(Subject).filter(
                    Subject.id.in_(subject_ids)).all()} if subject_ids else {}

    task_ids = {i.task_id for i in items if i.task_id}
    tasks_notes = {}
    if task_ids:
        tasks_notes = {t.id: t.note for t in db.query(TeachingTask).filter(
            TeachingTask.id.in_(task_ids)).all()}

    teacher_info = db.query(Teacher).filter(Teacher.id == teacher_id).first()

    timetable = {}
    for item in items:
        key = f"{item.day}-{item.period}"
        si = subjects.get(item.subject_id, {"name": "", "color": "#ccc"})
        timetable[key] = {
            "item_id": item.id,
            "subject_name": si["name"],
            "subject_color": si["color"],
            "class_name": classes.get(item.class_id, ""),
            "note": tasks_notes.get(item.task_id, "") or "",
            "is_locked": bool(item.is_locked),
        }

    # 查询该教师所属教研组的组会时间
    meeting_info = None
    if teacher_info and teacher_info.research_group_id:
        schedule = db.query(models.Schedule).filter(
            models.Schedule.id == schedule_id
        ).first()
        if schedule and schedule.meeting_info:
            gid_str = str(teacher_info.research_group_id)
            group_meeting = schedule.meeting_info.get(gid_str)
            if group_meeting:
                from app.modules.teachers.models import ResearchGroup
                rg = db.query(ResearchGroup).filter(
                    ResearchGroup.id == teacher_info.research_group_id
                ).first()
                meeting_info = {
                    "group_name": rg.name if rg else "",
                    "day": group_meeting["day"],
                    "periods": [group_meeting["period"], group_meeting["period"] + 1],
                }

    return {
        "code": 200,
        "data": {
            "teacher_id": teacher_id,
            "teacher_name": teacher_info.name if teacher_info else "",
            "timetable": timetable,
            "total_periods": len(items),
            "meeting_info": meeting_info,
        },
    }


@router.get("/{schedule_id}/by-venue/{venue_id}")
def get_venue_timetable(
    schedule_id: int, venue_id: int, db: Session = Depends(get_db),
):
    """获取指定场地的课表"""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="场地不存在")

    venue_subjects = venue.subjects or []
    if not venue_subjects:
        return {"code": 200, "data": {
            "venue_id": venue_id, "venue_name": venue.name,
            "timetable": {}, "total_periods": 0,
        }}

    subject_records = db.query(Subject).filter(
        Subject.name.in_(venue_subjects)).all()
    subject_id_map = {s.id: s for s in subject_records}

    if not subject_id_map:
        return {"code": 200, "data": {
            "venue_id": venue_id, "venue_name": venue.name,
            "timetable": {}, "total_periods": 0,
        }}

    items = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.subject_id.in_(subject_id_map.keys()),
    ).all()

    class_ids = {i.class_id for i in items if i.class_id}
    teacher_ids = {i.teacher_id for i in items if i.teacher_id}

    classes = {c.id: c.name for c in db.query(Class).filter(
        Class.id.in_(class_ids)).all()} if class_ids else {}
    teachers = {t.id: t.name for t in db.query(Teacher).filter(
        Teacher.id.in_(teacher_ids)).all()} if teacher_ids else {}

    timetable: dict = {}
    for item in items:
        key = f"{item.day}-{item.period}"
        si = subject_id_map.get(item.subject_id)
        if key not in timetable:
            timetable[key] = []
        timetable[key].append({
            "class_name": classes.get(item.class_id, ""),
            "teacher_name": teachers.get(item.teacher_id, ""),
            "subject_name": si.name if si else "",
            "subject_color": si.color if si else "#ccc",
        })

    return {
        "code": 200,
        "data": {
            "venue_id": venue_id,
            "venue_name": venue.name,
            "capacity": venue.capacity,
            "subjects": venue_subjects,
            "timetable": timetable,
            "total_periods": len(items),
        },
    }


# ===========================================================
#  课表操作
# ===========================================================

@router.put("/{schedule_id}/activate")
def activate_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """激活指定课表"""
    db.query(models.Schedule).update({"is_active": False})
    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课表不存在")
    schedule.is_active = True
    db.commit()
    return {"code": 200, "message": "课表已激活", "data": {"id": schedule_id}}


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """删除指定课表"""
    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课表不存在")
    db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id).delete()
    db.delete(schedule)
    db.commit()
    return {"code": 200, "message": "课表已删除"}


@router.get("/{schedule_id}/by-student/{student_id}")
def get_student_timetable(
    schedule_id: int, student_id: int, db: Session = Depends(get_db),
):
    """
    获取指定学生的个人课表

    包含两部分：
    1. 行政班课程（从 schedule_items 获取）
    2. A-Level 选修课程（从 course_classes.schedule_pattern 获取）
    """
    # 验证学生存在
    student = db.query(Student).filter(
        Student.id == student_id, Student.is_deleted == False
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 验证课表存在
    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课表不存在")

    timetable = {}

    # ===== Part 1: 行政班课程 =====
    if student.class_id:
        class_items = db.query(models.ScheduleItem).filter(
            models.ScheduleItem.schedule_id == schedule_id,
            models.ScheduleItem.class_id == student.class_id,
        ).all()

        teacher_ids = {i.teacher_id for i in class_items if i.teacher_id}
        subject_ids = {i.subject_id for i in class_items if i.subject_id}

        teachers = {t.id: t.name for t in db.query(Teacher).filter(
            Teacher.id.in_(teacher_ids)).all()} if teacher_ids else {}
        subjects = {s.id: {"name": s.name, "color": s.color}
                    for s in db.query(Subject).filter(
                        Subject.id.in_(subject_ids)).all()} if subject_ids else {}

        for item in class_items:
            key = f"{item.day}-{item.period}"
            si = subjects.get(item.subject_id, {"name": "", "color": "#ccc"})
            timetable[key] = {
                "item_id": item.id,
                "subject_name": si["name"],
                "subject_color": si["color"],
                "teacher_name": teachers.get(item.teacher_id, ""),
                "class_name": "",
                "note": "行政班课程",
                "is_locked": bool(item.is_locked),
                "type": "homeroom",
            }

    # ===== Part 2: A-Level 选修课程 =====
    # 查找学生已加入的所有课程班
    enrolled_class_ids = db.query(CourseClassMember.course_class_id).filter(
        CourseClassMember.student_id == student_id,
        CourseClassMember.status == "ENROLLED",
    ).all()
    enrolled_class_ids = [r[0] for r in enrolled_class_ids]

    if enrolled_class_ids:
        course_classes = db.query(CourseClass).filter(
            CourseClass.id.in_(enrolled_class_ids),
            CourseClass.is_deleted == False,
        ).all()

        for cc in course_classes:
            teacher_name = ""
            if cc.teacher_id:
                t = db.query(Teacher).filter(Teacher.id == cc.teacher_id).first()
                teacher_name = t.name if t else ""

            subject_name = cc.name
            alevel_sub = db.query(AlevelSubject).filter(
                AlevelSubject.id == cc.alevel_subject_id
            ).first()
            subject_color = "#8b5cf6"  # 默认紫色用于A-Level课程
            if alevel_sub:
                subject_name = alevel_sub.name

            # 解析 schedule_pattern 中的时间槽
            pattern = cc.schedule_pattern or {}
            slots = []
            if isinstance(pattern, dict):
                # 支持多种格式
                if "slots" in pattern and isinstance(pattern["slots"], list):
                    slots = pattern["slots"]
                elif "day" in pattern and "period" in pattern:
                    slots = [pattern]

            if slots:
                for slot in slots:
                    day = slot.get("day")
                    period = slot.get("period")
                    if day and period:
                        key = f"{day}-{period}"
                        # 如果同一时间段已有行政班课程，标记为冲突/叠加
                        existing = timetable.get(key)
                        if existing:
                            # 叠加显示：保留行政班，增加A-Level标记
                            existing["alevel_subject"] = subject_name
                            existing["alevel_teacher"] = teacher_name
                            existing["note"] = f"行政班: {existing['subject_name']} | A-Level: {subject_name}"
                        else:
                            timetable[key] = {
                                "item_id": None,
                                "subject_name": subject_name,
                                "subject_color": subject_color,
                                "teacher_name": teacher_name,
                                "class_name": cc.name,
                                "note": f"A-Level: {cc.name}",
                                "is_locked": False,
                                "type": "alevel",
                            }
            else:
                # schedule_pattern 没有时间信息，放到特殊标记中
                pass

    # 获取学生行政班名称
    class_name = ""
    if student.class_id:
        cls = db.query(Class).filter(Class.id == student.class_id).first()
        class_name = cls.name if cls else ""

    return {
        "code": 200,
        "data": {
            "student_id": student_id,
            "student_name": student.name,
            "student_no": student.student_no,
            "grade": student.grade,
            "class_name": class_name,
            "timetable": timetable,
            "total_periods": len(timetable),
        },
    }


@router.post("/{schedule_id}/swap")
def swap_schedule_items(
    schedule_id: int,
    item1_day: int = Query(...),
    item1_period: int = Query(...),
    item1_class_id: int = Query(...),
    item2_day: int = Query(...),
    item2_period: int = Query(...),
    item2_class_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """交换两个课程的位置（使用原生 SQL 避免唯一约束冲突）"""
    from sqlalchemy import text

    schedule = db.query(models.Schedule).filter(
        models.Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="课表不存在")

    item1 = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.day == item1_day,
        models.ScheduleItem.period == item1_period,
        models.ScheduleItem.class_id == item1_class_id,
    ).first()

    item2 = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.day == item2_day,
        models.ScheduleItem.period == item2_period,
        models.ScheduleItem.class_id == item2_class_id,
    ).first()

    if not item1 and not item2:
        return {"code": 200, "message": "两个位置都没有课程"}

    try:
        if item1 and item2:
            # 三步交换避免唯一约束冲突：
            # 1) item1 → 临时位置 (day=-1, period=-1)
            # 2) item2 → item1 的原位置
            # 3) item1 → item2 的原位置
            db.execute(text(
                "UPDATE schedule_items SET day = -1, period = -1 "
                "WHERE id = :id"
            ), {"id": item1.id})
            db.flush()

            db.execute(text(
                "UPDATE schedule_items SET day = :d, period = :p "
                "WHERE id = :id"
            ), {"id": item2.id, "d": item1_day, "p": item1_period})
            db.flush()

            db.execute(text(
                "UPDATE schedule_items SET day = :d, period = :p "
                "WHERE id = :id"
            ), {"id": item1.id, "d": item2_day, "p": item2_period})
        elif item1:
            item1.day, item1.period = item2_day, item2_period
        else:
            item2.day, item2.period = item1_day, item1_period

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"调换失败: {e}")

    return {"code": 200, "message": "课程调换成功"}


@router.post("/{schedule_id}/move")
def move_schedule_item(
    schedule_id: int,
    item_id: int = Query(...),
    to_day: int = Query(...),
    to_period: int = Query(...),
    db: Session = Depends(get_db),
):
    """移动课程到新位置"""
    item = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.id == item_id,
        models.ScheduleItem.schedule_id == schedule_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="课程不存在")

    existing = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.day == to_day,
        models.ScheduleItem.period == to_period,
        models.ScheduleItem.class_id == item.class_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="目标位置已有课程")

    conflict = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.day == to_day,
        models.ScheduleItem.period == to_period,
        models.ScheduleItem.teacher_id == item.teacher_id,
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail="教师时间冲突")

    item.day, item.period = to_day, to_period
    db.commit()
    return {"code": 200, "message": "课程移动成功"}


# ===========================================================
#  锁定/解锁
# ===========================================================

@router.put("/{schedule_id}/items/{item_id}/lock")
def toggle_lock_item(
    schedule_id: int,
    item_id: int,
    locked: bool = Query(True),
    db: Session = Depends(get_db),
):
    """锁定或解锁一个课程项"""
    item = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.id == item_id,
        models.ScheduleItem.schedule_id == schedule_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="课程项不存在")
    item.is_locked = locked
    db.commit()
    action = "已锁定" if locked else "已解锁"
    return {"code": 200, "message": f"课程{action}", "data": {"is_locked": locked}}


# ===========================================================
#  调换候选位置分析
# ===========================================================

@router.get("/{schedule_id}/swap-candidates")
def get_swap_candidates(
    schedule_id: int,
    day: int = Query(..., description="源课程星期"),
    period: int = Query(..., description="源课程节次"),
    class_id: int = Query(..., description="源课程班级ID"),
    db: Session = Depends(get_db),
):
    """分析指定课程可以调换到哪些位置"""
    # 加载源课程
    source = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
        models.ScheduleItem.day == day,
        models.ScheduleItem.period == period,
        models.ScheduleItem.class_id == class_id,
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="源课程不存在")

    # 加载整张课表所有 items
    all_items = db.query(models.ScheduleItem).filter(
        models.ScheduleItem.schedule_id == schedule_id,
    ).all()

    # 加载科目信息（判断主科、艺体等）
    subject_ids = {i.subject_id for i in all_items if i.subject_id}
    subjects = {s.id: s for s in db.query(Subject).filter(
        Subject.id.in_(subject_ids)).all()} if subject_ids else {}

    # 加载教师名和班级名用于消息
    teacher_ids = {i.teacher_id for i in all_items if i.teacher_id}
    teachers = {t.id: t.name for t in db.query(Teacher).filter(
        Teacher.id.in_(teacher_ids)).all()} if teacher_ids else {}
    class_ids_set = {i.class_id for i in all_items if i.class_id}
    classes = {c.id: c.name for c in db.query(Class).filter(
        Class.id.in_(class_ids_set)).all()} if class_ids_set else {}

    # 检查源课程是否属于分层组
    source_task = None
    if source.task_id:
        source_task = db.query(TeachingTask).filter(
            TeachingTask.id == source.task_id).first()

    source_subj = subjects.get(source.subject_id)
    source_subj_name = source_subj.name if source_subj else ""

    # 构建快速查询索引
    # teacher_slots: {(teacher_id, day, period): [item...]}
    from collections import defaultdict
    teacher_slots = defaultdict(list)
    class_slots = defaultdict(list)
    subj_day_count = defaultdict(int)  # (class_id, subject_id, day) -> count

    for it in all_items:
        if it.teacher_id:
            teacher_slots[(it.teacher_id, it.day, it.period)].append(it)
        if it.class_id:
            class_slots[(it.class_id, it.day, it.period)].append(it)
        if it.class_id and it.subject_id:
            subj_day_count[(it.class_id, it.subject_id, it.day)] += 1

    # 艺体关键词
    ART_PE = {'体育', '美术', '音乐', '声乐', '钢琴', '轮滑',
              '舞蹈', '艺术', 'PE', 'Art', 'Music'}

    def _analyze(td, tp):
        """分析 (td, tp) 位置能否放源课程"""
        conflicts = []
        warnings = []

        # 当前位置就是源 → 标记为自身
        if td == day and tp == period:
            return {"status": "self", "conflicts": [], "warnings": [],
                    "current_subject": source_subj_name}

        # 目标位置是否有同班课程（交换场景）
        target_item = None
        for it in class_slots.get((class_id, td, tp), []):
            if it.id != source.id:
                target_item = it
                break

        # 锁定检查
        if target_item and target_item.is_locked:
            conflicts.append("目标位置课程已锁定")
            target_subj = subjects.get(target_item.subject_id)
            return {
                "status": "locked",
                "current_subject": target_subj.name if target_subj else "",
                "current_teacher": teachers.get(target_item.teacher_id, ""),
                "conflicts": conflicts, "warnings": warnings,
            }

        # 分层组限制
        if source_task and source_task.layer_group_id:
            conflicts.append("分层课程需整组调换，暂不支持单独操作")

        # ---- 硬约束检查 ----
        # 1) 教师冲突: 源教师在 (td, tp) 是否有其他课
        for it in teacher_slots.get((source.teacher_id, td, tp), []):
            if it.id != source.id and it.class_id != class_id:
                conflicts.append(
                    f"教师 {teachers.get(source.teacher_id, '')} "
                    f"该时段已有 {classes.get(it.class_id, '')} 的课")
                break

        # 2) 交换场景: 目标课程教师在源位置是否有冲突
        if target_item and target_item.teacher_id:
            for it in teacher_slots.get(
                    (target_item.teacher_id, day, period), []):
                if it.id != target_item.id and it.class_id != class_id:
                    conflicts.append(
                        f"对方教师 {teachers.get(target_item.teacher_id, '')} "
                        f"在源时段有冲突")
                    break

        # 3) 同科目每日上限 (Tier2 H5)
        # 源课放到 td → 目标天该科目数 +1（去掉源天 -1）
        src_day_cnt = subj_day_count.get(
            (class_id, source.subject_id, td), 0)
        # 如果是交换且目标课和源课同科目，抵消
        add = 1
        if target_item and target_item.subject_id == source.subject_id:
            add = 0
        if src_day_cnt + add > 2:
            conflicts.append(
                f"{source_subj_name} 该天已有 {src_day_cnt} 节，超出每日2节上限")

        # 同理检查对方移到源天
        if target_item:
            tgt_subj = subjects.get(target_item.subject_id)
            tgt_day_cnt = subj_day_count.get(
                (class_id, target_item.subject_id, day), 0)
            add2 = 1
            if source.subject_id == target_item.subject_id:
                add2 = 0
            if tgt_day_cnt + add2 > 2 and tgt_subj:
                conflicts.append(
                    f"{tgt_subj.name} 在源天已有 {tgt_day_cnt} 节，"
                    f"交换后超出每日2节上限")

        # ---- 软约束检查 ----
        # S1: 主科未排上午
        if source_subj and source_subj.is_main and tp >= 6:
            warnings.append(f"主科「{source_subj_name}」排在下午（建议上午）")
        # S2: 艺体排第一节
        if source_subj and source_subj.name in ART_PE and tp == 1:
            warnings.append(f"「{source_subj_name}」排在第1节（建议避免）")

        # 确定状态
        target_subj = subjects.get(
            target_item.subject_id) if target_item else None
        status = "conflict" if conflicts else (
            "soft_risk" if warnings else "available")

        result = {
            "status": status,
            "current_subject": target_subj.name if target_subj else None,
            "current_teacher": teachers.get(
                target_item.teacher_id, "") if target_item else None,
            "conflicts": conflicts,
            "warnings": warnings,
        }
        if target_item and target_item.is_locked:
            result["status"] = "locked"
        return result

    # 遍历所有可能的位置
    candidates = {}
    for td in range(1, 6):
        for tp in range(1, 12):
            candidates[f"{td}-{tp}"] = _analyze(td, tp)

    return {
        "code": 200,
        "data": {
            "source": {
                "day": day, "period": period,
                "subject": source_subj_name,
                "teacher": teachers.get(source.teacher_id, ""),
            },
            "candidates": candidates,
        },
    }


# ===========================================================
#  约束验证
# ===========================================================

@router.get("/{schedule_id}/validate")
def validate_schedule(
    schedule_id: int,
    class_id: int = Query(None, description="限定班级视角"),
    db: Session = Depends(get_db),
):
    """验证课表约束违反情况"""
    from app.engine.validator import ScheduleValidator
    validator = ScheduleValidator(db, schedule_id, class_id=class_id)
    result = validator.validate()
    return {"code": 200, "data": result}
