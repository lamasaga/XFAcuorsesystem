"""
========================================
科目数据库操作
========================================
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.subjects.models import Subject
from app.modules.subjects.schemas import SubjectCreate, SubjectUpdate


def get_subject(db: Session, subject_id: int) -> Optional[Subject]:
    """根据 ID 获取科目"""
    return db.query(Subject).filter(Subject.id == subject_id, Subject.is_deleted == False).first()


def get_subject_by_code(db: Session, code: str) -> Optional[Subject]:
    """根据代码获取科目"""
    return db.query(Subject).filter(Subject.code == code, Subject.is_deleted == False).first()


def get_subjects(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    is_main: Optional[bool] = None
) -> List[Subject]:
    """获取科目列表"""
    query = db.query(Subject).filter(Subject.is_deleted == False)
    
    if category:
        query = query.filter(Subject.category == category)
    if is_main is not None:
        query = query.filter(Subject.is_main == is_main)
    
    return query.order_by(Subject.id).offset(skip).limit(limit).all()


def get_subjects_count(
    db: Session,
    category: Optional[str] = None,
    is_main: Optional[bool] = None
) -> int:
    """获取科目总数"""
    query = db.query(Subject).filter(Subject.is_deleted == False)
    
    if category:
        query = query.filter(Subject.category == category)
    if is_main is not None:
        query = query.filter(Subject.is_main == is_main)
    
    return query.count()


def create_subject(db: Session, subject: SubjectCreate) -> Subject:
    """创建科目"""
    db_subject = Subject(**subject.model_dump())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject


def update_subject(db: Session, subject_id: int, subject_update: SubjectUpdate) -> Optional[Subject]:
    """更新科目"""
    db_subject = get_subject(db, subject_id)
    if not db_subject:
        return None
    
    update_data = subject_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_subject, field, value)
    
    db.commit()
    db.refresh(db_subject)
    return db_subject


def delete_subject(db: Session, subject_id: int) -> bool:
    """删除科目"""
    db_subject = get_subject(db, subject_id)
    if not db_subject:
        return False
    
    db_subject.is_deleted = True
    db.commit()
    return True
