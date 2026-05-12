"""
========================================
课程班数据操作
========================================

提供课程班数据的增删改查操作。
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.course_classes.models import CourseClass, CourseClassMember
from app.modules.course_classes.schemas import (
    CourseClassCreate, CourseClassUpdate,
    CourseClassMemberCreate
)


def get_course_class(db: Session, class_id: int) -> Optional[CourseClass]:
    """根据ID获取课程班"""
    return db.query(CourseClass).filter(
        CourseClass.id == class_id,
        CourseClass.is_deleted == False
    ).first()


def get_course_classes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    alevel_subject_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    semester: Optional[str] = None,
    academic_year: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[CourseClass]:
    """获取课程班列表"""
    query = db.query(CourseClass).filter(CourseClass.is_deleted == False)
    
    if alevel_subject_id:
        query = query.filter(CourseClass.alevel_subject_id == alevel_subject_id)
    if teacher_id:
        query = query.filter(CourseClass.teacher_id == teacher_id)
    if semester:
        query = query.filter(CourseClass.semester == semester)
    if academic_year:
        query = query.filter(CourseClass.academic_year == academic_year)
    if status:
        query = query.filter(CourseClass.status == status)
    if search:
        query = query.filter(CourseClass.name.contains(search))
    
    return query.order_by(CourseClass.id.desc()).offset(skip).limit(limit).all()


def get_course_classes_count(
    db: Session,
    alevel_subject_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    semester: Optional[str] = None,
    academic_year: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """获取课程班总数"""
    query = db.query(CourseClass).filter(CourseClass.is_deleted == False)
    
    if alevel_subject_id:
        query = query.filter(CourseClass.alevel_subject_id == alevel_subject_id)
    if teacher_id:
        query = query.filter(CourseClass.teacher_id == teacher_id)
    if semester:
        query = query.filter(CourseClass.semester == semester)
    if academic_year:
        query = query.filter(CourseClass.academic_year == academic_year)
    if status:
        query = query.filter(CourseClass.status == status)
    if search:
        query = query.filter(CourseClass.name.contains(search))
    
    return query.count()


def create_course_class(db: Session, course_class: CourseClassCreate) -> CourseClass:
    """创建课程班"""
    db_class = CourseClass(
        alevel_subject_id=course_class.alevel_subject_id,
        teacher_id=course_class.teacher_id,
        name=course_class.name,
        code=course_class.code,
        max_capacity=course_class.max_capacity,
        current_enrollment=course_class.current_enrollment,
        semester=course_class.semester,
        academic_year=course_class.academic_year,
        schedule_pattern=course_class.schedule_pattern,
        status=course_class.status
    )
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


def update_course_class(
    db: Session,
    class_id: int,
    class_update: CourseClassUpdate
) -> Optional[CourseClass]:
    """更新课程班信息"""
    db_class = get_course_class(db, class_id)
    if not db_class:
        return None
    
    update_data = class_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_class, field, value)
    
    db.commit()
    db.refresh(db_class)
    return db_class


def delete_course_class(db: Session, class_id: int) -> bool:
    """删除课程班（软删除）"""
    db_class = get_course_class(db, class_id)
    if not db_class:
        return False
    
    db_class.is_deleted = True
    db.commit()
    return True


# ========== 课程班成员操作 ==========

def get_course_class_members(
    db: Session,
    course_class_id: int
) -> List[CourseClassMember]:
    """获取课程班成员列表"""
    return db.query(CourseClassMember).filter(
        CourseClassMember.course_class_id == course_class_id,
        CourseClassMember.status == "ENROLLED"
    ).all()


def add_course_class_member(
    db: Session,
    member: CourseClassMemberCreate
) -> CourseClassMember:
    """添加课程班成员"""
    db_member = CourseClassMember(
        course_class_id=member.course_class_id,
        student_id=member.student_id,
        status=member.status
    )
    db.add(db_member)
    
    # 更新课程班人数
    course_class = get_course_class(db, member.course_class_id)
    if course_class:
        course_class.current_enrollment += 1
    
    db.commit()
    db.refresh(db_member)
    return db_member


def remove_course_class_member(
    db: Session,
    member_id: int
) -> bool:
    """移除课程班成员"""
    db_member = db.query(CourseClassMember).filter(
        CourseClassMember.id == member_id
    ).first()
    if not db_member:
        return False
    
    db_member.status = "DROPPED"
    
    # 更新课程班人数
    course_class = get_course_class(db, db_member.course_class_id)
    if course_class and course_class.current_enrollment > 0:
        course_class.current_enrollment -= 1
    
    db.commit()
    return True
