"""
========================================
教学任务数据库操作
========================================
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.modules.tasks.models import TeachingTask
from app.modules.tasks.schemas import TeachingTaskCreate, TeachingTaskUpdate
from app.modules.teachers.models import Teacher
from app.modules.classes.models import Class
from app.modules.subjects.models import Subject


def get_task(db: Session, task_id: int) -> Optional[TeachingTask]:
    """根据 ID 获取任务"""
    return db.query(TeachingTask).filter(
        TeachingTask.id == task_id,
        TeachingTask.is_deleted == False
    ).first()


def get_tasks(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    teacher_id: Optional[int] = None,
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None
) -> List[TeachingTask]:
    """获取任务列表"""
    query = db.query(TeachingTask).filter(TeachingTask.is_deleted == False)
    
    if teacher_id:
        query = query.filter(TeachingTask.teacher_id == teacher_id)
    if class_id:
        query = query.filter(TeachingTask.class_id == class_id)
    if subject_id:
        query = query.filter(TeachingTask.subject_id == subject_id)
    
    return query.order_by(TeachingTask.id).offset(skip).limit(limit).all()


def get_tasks_count(
    db: Session,
    teacher_id: Optional[int] = None,
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None
) -> int:
    """获取任务总数"""
    query = db.query(TeachingTask).filter(TeachingTask.is_deleted == False)
    
    if teacher_id:
        query = query.filter(TeachingTask.teacher_id == teacher_id)
    if class_id:
        query = query.filter(TeachingTask.class_id == class_id)
    if subject_id:
        query = query.filter(TeachingTask.subject_id == subject_id)
    
    return query.count()


def get_tasks_with_details(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    class_id: Optional[int] = None,
    grade: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取包含详细信息的任务列表
    
    联表查询获取教师名、班级名、科目名等信息。
    """
    # 联表查询
    query = db.query(
        TeachingTask,
        Teacher.name.label("teacher_name"),
        Teacher.type.label("teacher_type"),
        Class.name.label("class_name"),
        Class.grade.label("class_grade"),
        Subject.name.label("subject_name"),
        Subject.code.label("subject_code")
    ).join(
        Teacher, TeachingTask.teacher_id == Teacher.id
    ).join(
        Class, TeachingTask.class_id == Class.id
    ).join(
        Subject, TeachingTask.subject_id == Subject.id
    ).filter(
        TeachingTask.is_deleted == False,
        Teacher.is_deleted == False,
        Class.is_deleted == False,
        Subject.is_deleted == False
    )
    
    if class_id:
        query = query.filter(TeachingTask.class_id == class_id)
    if grade:
        query = query.filter(Class.grade == grade)
    
    results = query.order_by(Class.grade, Class.name, Subject.name).offset(skip).limit(limit).all()
    
    # 转换为字典列表
    tasks = []
    for row in results:
        task = row[0]  # TeachingTask 对象
        tasks.append({
            "id": task.id,
            "teacher_id": task.teacher_id,
            "class_id": task.class_id,
            "subject_id": task.subject_id,
            "weekly_hours": task.weekly_hours,
            "is_continuous": task.is_continuous,
            "continuous_count": task.continuous_count,
            "preferred_period": task.preferred_period,
            "note": task.note,
            "teacher_name": row.teacher_name,
            "teacher_type": row.teacher_type,
            "class_name": row.class_name,
            "class_grade": row.class_grade,
            "subject_name": row.subject_name,
            "subject_code": row.subject_code
        })
    
    return tasks


def check_task_exists(
    db: Session,
    teacher_id: int,
    class_id: int,
    subject_id: int
) -> bool:
    """检查任务是否已存在"""
    return db.query(TeachingTask).filter(
        and_(
            TeachingTask.teacher_id == teacher_id,
            TeachingTask.class_id == class_id,
            TeachingTask.subject_id == subject_id,
            TeachingTask.is_deleted == False
        )
    ).first() is not None


def create_task(db: Session, task: TeachingTaskCreate) -> TeachingTask:
    """创建任务"""
    db_task = TeachingTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task_id: int, task_update: TeachingTaskUpdate) -> Optional[TeachingTask]:
    """更新任务"""
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> bool:
    """删除任务"""
    db_task = get_task(db, task_id)
    if not db_task:
        return False
    
    db_task.is_deleted = True
    db.commit()
    return True


def create_tasks_batch(db: Session, tasks: List[TeachingTaskCreate]) -> List[TeachingTask]:
    """批量创建任务"""
    db_tasks = [TeachingTask(**t.model_dump()) for t in tasks]
    db.add_all(db_tasks)
    db.commit()
    for t in db_tasks:
        db.refresh(t)
    return db_tasks
