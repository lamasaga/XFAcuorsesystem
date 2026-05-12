from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.dependencies import get_db
from . import schemas, crud, models

router = APIRouter(
    tags=["场地资源 (Venue Resources)"]
)


def serialize_venue(venue: models.Venue) -> dict:
    """将 Venue ORM 对象转换为字典"""
    return schemas.VenueResponse.model_validate(venue).model_dump()


@router.get("/", response_model=dict)
def read_venues(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取场地列表"""
    venues = crud.get_venues(db, skip=skip, limit=limit)
    # 获取真实总数
    total = db.query(func.count(models.Venue.id)).scalar()
    # 序列化所有场地
    items = [serialize_venue(v) for v in venues]
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total
        }
    }


@router.get("/{venue_id}", response_model=dict)
def read_venue(
    venue_id: int,
    db: Session = Depends(get_db)
):
    """获取单个场地详情"""
    venue = crud.get_venue(db, venue_id)
    if not venue:
        raise HTTPException(status_code=404, detail="场地不存在")
    return {
        "code": 200,
        "message": "success",
        "data": serialize_venue(venue)
    }


@router.post("/", response_model=dict)
def create_venue(
    venue: schemas.VenueCreate, 
    db: Session = Depends(get_db)
):
    """创建场地"""
    new_venue = crud.create_venue(db, venue=venue)
    return {
        "code": 200,
        "message": "success",
        "data": serialize_venue(new_venue)
    }


@router.put("/{venue_id}", response_model=dict)
def update_venue(
    venue_id: int,
    venue: schemas.VenueUpdate,
    db: Session = Depends(get_db)
):
    """更新场地"""
    updated_venue = crud.update_venue(db, venue_id, venue)
    if not updated_venue:
        raise HTTPException(status_code=404, detail="场地不存在")
    return {
        "code": 200,
        "message": "success",
        "data": serialize_venue(updated_venue)
    }


@router.delete("/{venue_id}", response_model=dict)
def delete_venue(
    venue_id: int, 
    db: Session = Depends(get_db)
):
    """删除场地"""
    deleted = crud.delete_venue(db, venue_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="场地不存在")
    return {"code": 200, "message": "success"}
