"""
========================================
选课数据操作
========================================

提供选课数据的增删改查操作。
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.course_selections.models import CourseSelection
from app.modules.course_selections.schemas import CourseSelectionCreate, CourseSelectionUpdate
from app.modules.alevel_subjects.models import AlevelSubject


def get_course_selection(db: Session, selection_id: int) -> Optional[CourseSelection]:
    """根据ID获取选课记录"""
    return db.query(CourseSelection).filter(
        CourseSelection.id == selection_id,
        CourseSelection.is_deleted == False
    ).first()


def get_course_selections(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    student_id: Optional[int] = None,
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
    status: Optional[str] = None
) -> List[CourseSelection]:
    """获取选课记录列表"""
    query = db.query(CourseSelection).filter(CourseSelection.is_deleted == False)
    
    if student_id:
        query = query.filter(CourseSelection.student_id == student_id)
    if academic_year:
        query = query.filter(CourseSelection.academic_year == academic_year)
    if semester:
        query = query.filter(CourseSelection.semester == semester)
    if status:
        query = query.filter(CourseSelection.status == status)
    
    return query.order_by(CourseSelection.id.desc()).offset(skip).limit(limit).all()


def get_course_selections_count(
    db: Session,
    student_id: Optional[int] = None,
    academic_year: Optional[str] = None,
    semester: Optional[str] = None,
    status: Optional[str] = None
) -> int:
    """获取选课记录总数"""
    query = db.query(CourseSelection).filter(CourseSelection.is_deleted == False)
    
    if student_id:
        query = query.filter(CourseSelection.student_id == student_id)
    if academic_year:
        query = query.filter(CourseSelection.academic_year == academic_year)
    if semester:
        query = query.filter(CourseSelection.semester == semester)
    if status:
        query = query.filter(CourseSelection.status == status)
    
    return query.count()


def create_course_selection(db: Session, selection: CourseSelectionCreate) -> CourseSelection:
    """创建选课记录"""
    # 计算总周课时：从 alevel_subjects 表查询每个科目的 weekly_hours
    subject_ids = [item.alevel_subject_id for item in (selection.selections or [])]
    subjects = db.query(AlevelSubject).filter(
        AlevelSubject.id.in_(subject_ids),
        AlevelSubject.is_deleted == False
    ).all() if subject_ids else []
    subject_hours = {s.id: s.weekly_hours for s in subjects}
    total_hours = sum(
        subject_hours.get(item.alevel_subject_id, 4)
        for item in (selection.selections or [])
    )
    
    db_selection = CourseSelection(
        student_id=selection.student_id,
        academic_year=selection.academic_year,
        semester=selection.semester,
        status=selection.status,
        selections=[s.model_dump() for s in selection.selections] if selection.selections else [],
        total_weekly_hours=selection.total_weekly_hours or total_hours,
        note=selection.note
    )
    db.add(db_selection)
    db.commit()
    db.refresh(db_selection)
    return db_selection


def update_course_selection(
    db: Session,
    selection_id: int,
    selection_update: CourseSelectionUpdate
) -> Optional[CourseSelection]:
    """更新选课记录"""
    db_selection = get_course_selection(db, selection_id)
    if not db_selection:
        return None
    
    update_data = selection_update.model_dump(exclude_unset=True)
    
    # 如果更新了选课列表，重新序列化
    if "selections" in update_data and update_data["selections"] is not None:
        update_data["selections"] = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in update_data["selections"]
        ]
    
    for field, value in update_data.items():
        setattr(db_selection, field, value)
    
    db.commit()
    db.refresh(db_selection)
    return db_selection


def delete_course_selection(db: Session, selection_id: int) -> bool:
    """删除选课记录（软删除）"""
    db_selection = get_course_selection(db, selection_id)
    if not db_selection:
        return False
    
    db_selection.is_deleted = True
    db.commit()
    return True
