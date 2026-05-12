"""
========================================
学生数据操作
========================================

提供学生数据的增删改查操作。
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.students.models import Student
from app.modules.students.schemas import StudentCreate, StudentUpdate


def get_student(db: Session, student_id: int) -> Optional[Student]:
    """根据ID获取学生"""
    return db.query(Student).filter(
        Student.id == student_id,
        Student.is_deleted == False
    ).first()


def get_student_by_no(db: Session, student_no: str) -> Optional[Student]:
    """根据学号获取学生"""
    return db.query(Student).filter(
        Student.student_no == student_no,
        Student.is_deleted == False
    ).first()


def get_students(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    grade: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[Student]:
    """获取学生列表"""
    query = db.query(Student).filter(Student.is_deleted == False)
    
    if grade:
        query = query.filter(Student.grade == grade)
    if status:
        query = query.filter(Student.status == status)
    if search:
        query = query.filter(Student.name.contains(search))
    
    return query.order_by(Student.id.desc()).offset(skip).limit(limit).all()


def get_students_count(
    db: Session,
    grade: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """获取学生总数"""
    query = db.query(Student).filter(Student.is_deleted == False)
    
    if grade:
        query = query.filter(Student.grade == grade)
    if status:
        query = query.filter(Student.status == status)
    if search:
        query = query.filter(Student.name.contains(search))
    
    return query.count()


def create_student(db: Session, student: StudentCreate) -> Student:
    """创建学生"""
    db_student = Student(
        name=student.name,
        student_no=student.student_no,
        grade=student.grade,
        class_id=student.class_id,
        status=student.status
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def create_students_batch(db: Session, students: List[StudentCreate]) -> List[Student]:
    """批量创建学生"""
    db_students = []
    for s in students:
        db_student = Student(
            name=s.name,
            student_no=s.student_no,
            grade=s.grade,
            class_id=s.class_id,
            status=s.status
        )
        db.add(db_student)
        db_students.append(db_student)
    db.commit()
    for db_student in db_students:
        db.refresh(db_student)
    return db_students


def update_student(
    db: Session,
    student_id: int,
    student_update: StudentUpdate
) -> Optional[Student]:
    """更新学生信息"""
    db_student = get_student(db, student_id)
    if not db_student:
        return None
    
    update_data = student_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_student, field, value)
    
    db.commit()
    db.refresh(db_student)
    return db_student


def delete_student(db: Session, student_id: int) -> bool:
    """删除学生（软删除）"""
    db_student = get_student(db, student_id)
    if not db_student:
        return False
    
    db_student.is_deleted = True
    db.commit()
    return True
