"""
========================================
班级管理 API 路由
========================================
"""

import re
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.core.dependencies import get_db, create_response, create_pagination_response
from app.modules.classes import crud
from app.modules.classes.models import Class
from app.modules.classes.schemas import ClassCreate, ClassUpdate, ClassResponse

router = APIRouter()


def _parse_grade_from_name(name: str) -> Optional[str]:
    """从班级名称解析年级（容错处理）"""
    if not name:
        return None
    # 匹配 IPK-1, IKG-1, IG3-1, NG2-1 等格式
    match = re.match(r'[IN]?(PK|KG|G\d+)', name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _ensure_grade(cls_dict: dict) -> dict:
    """确保班级数据包含 grade 字段"""
    if not cls_dict.get('grade') and cls_dict.get('name'):
        cls_dict['grade'] = _parse_grade_from_name(cls_dict['name'])
    return cls_dict


def _fix_deleted_class_name(db: Session, name: str) -> bool:
    """
    修复已软删除但未重命名的班级记录
    
    如果存在同名但已删除的班级，将其重命名以释放名称。
    这是为了兼容旧版本软删除逻辑产生的历史数据。
    
    Returns:
        True 如果进行了修复，False 如果无需修复
    """
    # 查找同名但已删除的记录
    deleted_class = db.query(Class).filter(
        Class.name == name,
        Class.is_deleted == True
    ).first()
    
    if deleted_class:
        # 重命名已删除的记录，释放原名称
        # 使用 "_D[ID]" 格式，确保不超过 20 字符且唯一
        deleted_class.name = f"_D{deleted_class.id}"
        db.commit()
        return True
    return False


@router.get("/")
async def get_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    type: Optional[str] = Query(None, description="班级类型：I/N"),
    department: Optional[str] = Query(None, description="学部"),
    grade: Optional[str] = Query(None, description="年级"),
    db: Session = Depends(get_db)
):
    """获取班级列表"""
    skip = (page - 1) * page_size
    classes = crud.get_classes(db, skip=skip, limit=page_size, type=type, department=department, grade=grade)
    total = crud.get_classes_count(db, type=type, department=department, grade=grade)
    # 确保每个班级都有 grade 字段（从名称解析作为容错）
    items = [_ensure_grade(ClassResponse.model_validate(c).model_dump()) for c in classes]
    return create_pagination_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/{class_id}")
async def get_class(class_id: int, db: Session = Depends(get_db)):
    """获取单个班级"""
    cls = crud.get_class(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail=f"班级不存在 (ID: {class_id})")
    return create_response(data=_ensure_grade(ClassResponse.model_validate(cls).model_dump()))


@router.post("/")
async def create_class(class_data: ClassCreate, db: Session = Depends(get_db)):
    """创建班级"""
    # 检查名称是否重复（只检查未删除的）
    existing = crud.get_class_by_name(db, class_data.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"班级名称已存在: {class_data.name}")
    
    try:
        new_class = crud.create_class(db, class_data)
        return create_response(data=ClassResponse.model_validate(new_class).model_dump(), message="创建成功")
    except IntegrityError as e:
        db.rollback()
        # 处理数据库唯一约束冲突
        if "classes_name_key" in str(e):
            # 尝试自动修复：可能是旧版本软删除的记录没有重命名
            if _fix_deleted_class_name(db, class_data.name):
                # 修复成功，重试创建
                try:
                    new_class = crud.create_class(db, class_data)
                    return create_response(data=ClassResponse.model_validate(new_class).model_dump(), message="创建成功")
                except IntegrityError:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=f"班级名称已存在: {class_data.name}")
            raise HTTPException(status_code=400, detail=f"班级名称已存在: {class_data.name}")
        raise HTTPException(status_code=400, detail="数据冲突，请检查输入")


@router.put("/{class_id}")
async def update_class(class_id: int, class_update: ClassUpdate, db: Session = Depends(get_db)):
    """更新班级"""
    updated = crud.update_class(db, class_id, class_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"班级不存在 (ID: {class_id})")
    return create_response(data=ClassResponse.model_validate(updated).model_dump(), message="更新成功")


@router.delete("/{class_id}")
async def delete_class(class_id: int, db: Session = Depends(get_db)):
    """删除班级"""
    success = crud.delete_class(db, class_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"班级不存在 (ID: {class_id})")
    return create_response(message="删除成功")
