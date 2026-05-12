"""
========================================
A-Level 科目数据操作
========================================

提供 A-Level 科目数据的增删改查操作。
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.alevel_subjects.models import AlevelSubject
from app.modules.alevel_subjects.schemas import AlevelSubjectCreate, AlevelSubjectUpdate


def get_alevel_subject(db: Session, subject_id: int) -> Optional[AlevelSubject]:
    """根据ID获取 A-Level 科目"""
    return db.query(AlevelSubject).filter(
        AlevelSubject.id == subject_id,
        AlevelSubject.is_deleted == False
    ).first()


def get_alevel_subjects(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    exam_board: Optional[str] = None,
    level: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[AlevelSubject]:
    """获取 A-Level 科目列表"""
    query = db.query(AlevelSubject).filter(AlevelSubject.is_deleted == False)
    
    if exam_board:
        query = query.filter(AlevelSubject.exam_board == exam_board)
    if level:
        query = query.filter(AlevelSubject.level == level)
    if is_active is not None:
        query = query.filter(AlevelSubject.is_active == is_active)
    if search:
        query = query.filter(AlevelSubject.name.contains(search))
    
    return query.order_by(AlevelSubject.id.desc()).offset(skip).limit(limit).all()


def get_alevel_subjects_count(
    db: Session,
    exam_board: Optional[str] = None,
    level: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> int:
    """获取 A-Level 科目总数"""
    query = db.query(AlevelSubject).filter(AlevelSubject.is_deleted == False)
    
    if exam_board:
        query = query.filter(AlevelSubject.exam_board == exam_board)
    if level:
        query = query.filter(AlevelSubject.level == level)
    if is_active is not None:
        query = query.filter(AlevelSubject.is_active == is_active)
    if search:
        query = query.filter(AlevelSubject.name.contains(search))
    
    return query.count()


def create_alevel_subject(db: Session, subject: AlevelSubjectCreate) -> AlevelSubject:
    """创建 A-Level 科目"""
    db_subject = AlevelSubject(
        subject_id=subject.subject_id,
        exam_board=subject.exam_board,
        level=subject.level,
        module_code=subject.module_code,
        name=subject.name,
        weekly_hours=subject.weekly_hours,
        max_students=subject.max_students,
        is_active=subject.is_active,
        description=subject.description
    )
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


def update_alevel_subject(
    db: Session,
    subject_id: int,
    subject_update: AlevelSubjectUpdate
) -> Optional[AlevelSubject]:
    """更新 A-Level 科目信息"""
    db_subject = get_alevel_subject(db, subject_id)
    if not db_subject:
        return None
    
    update_data = subject_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_subject, field, value)
    
    db.commit()
    db.refresh(db_subject)
    return db_subject


def delete_alevel_subject(db: Session, subject_id: int) -> bool:
    """删除 A-Level 科目（软删除）"""
    db_subject = get_alevel_subject(db, subject_id)
    if not db_subject:
        return False
    
    db_subject.is_deleted = True
    db.commit()
    return True
