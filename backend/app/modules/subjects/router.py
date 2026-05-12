"""
========================================
科目管理 API 路由
========================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.core.dependencies import get_db, create_response, create_pagination_response
from app.core.importer import create_import_response
from app.modules.subjects import crud
from app.modules.subjects.schemas import SubjectCreate, SubjectUpdate, SubjectResponse
from app.modules.subjects import service_import as import_service

router = APIRouter()


@router.get("/")
async def get_subjects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="分类过滤"),
    is_main: Optional[bool] = Query(None, description="是否主科"),
    db: Session = Depends(get_db)
):
    """获取科目列表"""
    skip = (page - 1) * page_size
    subjects = crud.get_subjects(db, skip=skip, limit=page_size, category=category, is_main=is_main)
    total = crud.get_subjects_count(db, category=category, is_main=is_main)
    items = [SubjectResponse.model_validate(s).model_dump() for s in subjects]
    return create_pagination_response(items=items, total=total, page=page, page_size=page_size)


# ── 导入导出 ── 必须在 /{subject_id} 之前注册 ──────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载科目导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "subjects_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "subjects_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_subjects(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入科目"""
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

    dup_errors = import_service.validate_unique_subjects(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在重复科目代码",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(dup_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in dup_errors],
            },
        }

    result = import_service.import_subjects_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{subject_id}")
async def get_subject(subject_id: int, db: Session = Depends(get_db)):
    """获取单个科目"""
    subject = crud.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail=f"科目不存在 (ID: {subject_id})")
    return create_response(data=SubjectResponse.model_validate(subject).model_dump())


@router.post("/")
async def create_subject(subject: SubjectCreate, db: Session = Depends(get_db)):
    """创建科目"""
    existing = crud.get_subject_by_code(db, subject.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"科目代码已存在: {subject.code}")
    
    new_subject = crud.create_subject(db, subject)
    return create_response(data=SubjectResponse.model_validate(new_subject).model_dump(), message="创建成功")


@router.put("/{subject_id}")
async def update_subject(subject_id: int, subject_update: SubjectUpdate, db: Session = Depends(get_db)):
    """更新科目"""
    updated = crud.update_subject(db, subject_id, subject_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"科目不存在 (ID: {subject_id})")
    return create_response(data=SubjectResponse.model_validate(updated).model_dump(), message="更新成功")


@router.delete("/{subject_id}")
async def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    """删除科目"""
    success = crud.delete_subject(db, subject_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"科目不存在 (ID: {subject_id})")
    return create_response(message="删除成功")
