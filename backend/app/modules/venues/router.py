from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.dependencies import get_db
from app.core.importer import create_import_response
from . import schemas, crud, models
from . import service_import as import_service

router = APIRouter(
    tags=["场地资源 (Venue Resources)"]
)


def serialize_venue(venue: models.Venue) -> dict:
    """将 Venue ORM 对象转换为字典"""
    return schemas.VenueResponse.model_validate(venue).model_dump()


@router.get("/", response_model=dict)
def read_venues(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取场地列表"""
    skip = (page - 1) * page_size
    venues = crud.get_venues(db, skip=skip, limit=page_size)
    # 获取真实总数
    total = db.query(func.count(models.Venue.id)).scalar()
    # 序列化所有场地
    items = [serialize_venue(v) for v in venues]
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
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


# ── 导入导出 ───────────────────────────────────────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载场地导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "venues_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "venues_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_venues(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入场地"""
    content = await file.read()
    rows, parse_errors = import_service.parse_import_file(file.filename or "", content)
    if parse_errors:
        return {
            "code": 400,
            "message": "导入失败：文件解析错误",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(parse_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in parse_errors],
            },
        }

    dup_errors = import_service.validate_unique_venues(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在重复场地名称",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(dup_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in dup_errors],
            },
        }

    result = import_service.import_venues_from_rows(db, rows)
    return create_import_response(result)
