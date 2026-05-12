from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional

def get_layer_group(db: Session, group_id: int):
    return db.query(models.LayerGroup).filter(models.LayerGroup.id == group_id).first()

def get_layer_groups(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    grade: Optional[str] = None
):
    query = db.query(models.LayerGroup)
    
    # 如果提供了年级筛选 (这里简化处理，检查是否包含)
    # 实际生产中数组包含查询可能需要特定语法，这里先做基础列表
    
    return query.offset(skip).limit(limit).all()

def create_layer_group(db: Session, group: schemas.LayerGroupCreate):
    db_group = models.LayerGroup(**group.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

def delete_layer_group(db: Session, group_id: int):
    group = get_layer_group(db, group_id)
    if group:
        db.delete(group)
        db.commit()
    return group

def update_layer_group(db: Session, group_id: int, group_update: schemas.LayerGroupUpdate):
    db_group = get_layer_group(db, group_id)
    if not db_group:
        return None
    
    update_data = group_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_group, key, value)
    
    db.commit()
    db.refresh(db_group)
    return db_group
