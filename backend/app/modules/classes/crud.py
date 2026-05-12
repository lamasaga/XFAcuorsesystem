"""
========================================
班级数据库操作（CRUD）
========================================

班主任同步逻辑：
- 当班级设置班主任时，自动给教师添加 HOMEROOM_TEACHER 标签
- 当班级移除班主任时，检查教师是否还是其他班级的班主任，如果不是则移除标签
- 这样保证排课约束可以正确识别班主任身份

软删除命名策略：
- 软删除时将班级名称重命名为 "[原名称]_DELETED_[时间戳]"
- 这样可以避免唯一约束冲突，同时保留历史记录
"""

import time
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from app.modules.classes.models import Class
from app.modules.classes.schemas import ClassCreate, ClassUpdate
from app.modules.teachers.models import Teacher


HOMEROOM_TAG = "HOMEROOM_TEACHER"


def _get_all_homeroom_teacher_ids(db: Session) -> Set[int]:
    """获取所有班级的班主任教师 ID 集合"""
    classes = db.query(Class).filter(Class.is_deleted == False).all()
    ids = set()
    for cls in classes:
        if cls.homeroom_cn_id:
            ids.add(cls.homeroom_cn_id)
        if cls.homeroom_en_id:
            ids.add(cls.homeroom_en_id)
    return ids


def _sync_homeroom_tag(db: Session, teacher_id: int, should_be_homeroom: bool) -> None:
    """同步教师的班主任标签"""
    if not teacher_id:
        return
    
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        return
    
    tags = teacher.tags or []
    has_tag = HOMEROOM_TAG in tags
    
    if should_be_homeroom and not has_tag:
        # 需要添加标签
        teacher.tags = tags + [HOMEROOM_TAG]
    elif not should_be_homeroom and has_tag:
        # 需要移除标签
        teacher.tags = [t for t in tags if t != HOMEROOM_TAG]


def _update_homeroom_tags(
    db: Session, 
    old_cn_id: Optional[int], 
    old_en_id: Optional[int],
    new_cn_id: Optional[int], 
    new_en_id: Optional[int]
) -> None:
    """
    更新班主任标签
    
    当班级的班主任发生变化时调用此函数：
    1. 新班主任：添加 HOMEROOM_TEACHER 标签
    2. 旧班主任：检查是否还是其他班级的班主任，如果不是则移除标签
    """
    # 获取当前所有班主任 ID（不包括即将被移除的）
    all_homeroom_ids = _get_all_homeroom_teacher_ids(db)
    
    # 处理新班主任
    if new_cn_id:
        _sync_homeroom_tag(db, new_cn_id, True)
    if new_en_id:
        _sync_homeroom_tag(db, new_en_id, True)
    
    # 处理旧班主任（如果被替换或移除）
    if old_cn_id and old_cn_id != new_cn_id:
        # 检查是否还是其他班级的班主任
        still_homeroom = old_cn_id in all_homeroom_ids and old_cn_id != old_cn_id
        # 更精确的检查：排除当前班级后是否还是班主任
        other_classes = db.query(Class).filter(
            Class.is_deleted == False,
            (Class.homeroom_cn_id == old_cn_id) | (Class.homeroom_en_id == old_cn_id)
        ).count()
        # 如果只有一个班级（即当前班级），则移除标签
        _sync_homeroom_tag(db, old_cn_id, other_classes > 1)
    
    if old_en_id and old_en_id != new_en_id:
        other_classes = db.query(Class).filter(
            Class.is_deleted == False,
            (Class.homeroom_cn_id == old_en_id) | (Class.homeroom_en_id == old_en_id)
        ).count()
        _sync_homeroom_tag(db, old_en_id, other_classes > 1)


def get_class(db: Session, class_id: int) -> Optional[Class]:
    """根据 ID 获取班级"""
    return db.query(Class).filter(Class.id == class_id, Class.is_deleted == False).first()


def get_class_by_name(db: Session, name: str) -> Optional[Class]:
    """根据名称获取班级"""
    return db.query(Class).filter(Class.name == name, Class.is_deleted == False).first()


def get_classes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    type: Optional[str] = None,
    department: Optional[str] = None,
    grade: Optional[str] = None
) -> List[Class]:
    """获取班级列表"""
    query = db.query(Class).filter(Class.is_deleted == False)
    
    if type:
        query = query.filter(Class.type == type)
    if department:
        query = query.filter(Class.department == department)
    if grade:
        query = query.filter(Class.grade == grade)
    
    return query.order_by(Class.grade, Class.class_no).offset(skip).limit(limit).all()


def get_classes_count(
    db: Session,
    type: Optional[str] = None,
    department: Optional[str] = None,
    grade: Optional[str] = None
) -> int:
    """获取班级总数"""
    query = db.query(Class).filter(Class.is_deleted == False)
    
    if type:
        query = query.filter(Class.type == type)
    if department:
        query = query.filter(Class.department == department)
    if grade:
        query = query.filter(Class.grade == grade)
    
    return query.count()


def create_class(db: Session, class_data: ClassCreate) -> Class:
    """创建班级，并同步班主任标签"""
    db_class = Class(**class_data.model_dump())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    
    # 同步班主任标签
    _update_homeroom_tags(
        db, 
        None, None,  # 新建班级没有旧班主任
        db_class.homeroom_cn_id, 
        db_class.homeroom_en_id
    )
    db.commit()
    
    return db_class


def update_class(db: Session, class_id: int, class_update: ClassUpdate) -> Optional[Class]:
    """更新班级，并同步班主任标签"""
    db_class = get_class(db, class_id)
    if not db_class:
        return None
    
    # 保存旧的班主任 ID
    old_cn_id = db_class.homeroom_cn_id
    old_en_id = db_class.homeroom_en_id
    
    update_data = class_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_class, field, value)
    
    db.commit()
    db.refresh(db_class)
    
    # 同步班主任标签
    _update_homeroom_tags(
        db, 
        old_cn_id, old_en_id,
        db_class.homeroom_cn_id, 
        db_class.homeroom_en_id
    )
    db.commit()
    
    return db_class


def delete_class(db: Session, class_id: int) -> bool:
    """
    删除班级（软删除），并同步班主任标签
    
    软删除策略：
    - 将 is_deleted 设为 True
    - 重命名班级名称为 "_D[ID]" 格式（如 "_D123"）
    - 这样可以释放原名称供新班级使用，同时保留历史记录
    - 使用短格式是因为 name 字段限制 20 字符
    """
    db_class = get_class(db, class_id)
    if not db_class:
        return False
    
    # 保存旧的班主任 ID
    old_cn_id = db_class.homeroom_cn_id
    old_en_id = db_class.homeroom_en_id
    
    # 软删除：标记删除并重命名，释放原名称
    # 使用 "_D[ID]" 格式，确保不超过 20 字符且唯一
    db_class.is_deleted = True
    db_class.name = f"_D{db_class.id}"
    db.commit()
    
    # 同步班主任标签（移除旧班主任的标签，如果他们不再是其他班级的班主任）
    _update_homeroom_tags(db, old_cn_id, old_en_id, None, None)
    db.commit()
    
    return True
