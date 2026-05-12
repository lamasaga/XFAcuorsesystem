"""
========================================
A-Level 科目管理 API 路由
========================================

API 接口列表：
- GET    /api/v1/alevel-subjects         获取 A-Level 科目列表
- GET    /api/v1/alevel-subjects/{id}    获取单个科目详情
- POST   /api/v1/alevel-subjects         创建新科目
- PUT    /api/v1/alevel-subjects/{id}    更新科目信息
- DELETE /api/v1/alevel-subjects/{id}    删除科目
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import (
    get_db,
    create_response,
    create_pagination_response
)
from app.core.importer import create_import_response
from app.modules.alevel_subjects import crud
from app.modules.alevel_subjects.schemas import (
    AlevelSubjectCreate,
    AlevelSubjectUpdate,
    AlevelSubjectResponse,
    AlevelSubjectListResponse,
    SimpleResponse,
)
from app.modules.alevel_subjects import service_import as import_service

router = APIRouter()


@router.get("/", response_model=AlevelSubjectListResponse)
async def get_alevel_subjects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量"),
    exam_board: Optional[str] = Query(None, description="考试局：CAIE/Edexcel/AQA"),
    level: Optional[str] = Query(None, description="级别：AS/A2"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取 A-Level 科目列表"""
    skip = (page - 1) * page_size
    subjects = crud.get_alevel_subjects(
        db,
        skip=skip,
        limit=page_size,
        exam_board=exam_board,
        level=level,
        is_active=is_active,
        search=search
    )
    total = crud.get_alevel_subjects_count(
        db,
        exam_board=exam_board,
        level=level,
        is_active=is_active,
        search=search
    )
    items = [AlevelSubjectResponse.model_validate(s).model_dump() for s in subjects]
    return create_pagination_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{subject_id}", response_model=dict)
async def get_alevel_subject(
    subject_id: int,
    db: Session = Depends(get_db)
):
    """获取单个 A-Level 科目详情"""
    subject = crud.get_alevel_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail=f"科目不存在 (ID: {subject_id})")
    return create_response(
        data=AlevelSubjectResponse.model_validate(subject).model_dump()
    )


@router.post("/", response_model=dict)
async def create_alevel_subject(
    subject: AlevelSubjectCreate,
    db: Session = Depends(get_db)
):
    """创建 A-Level 科目"""
    new_subject = crud.create_alevel_subject(db, subject)
    return create_response(
        data=AlevelSubjectResponse.model_validate(new_subject).model_dump(),
        message="创建成功"
    )


@router.put("/{subject_id}", response_model=dict)
async def update_alevel_subject(
    subject_id: int,
    subject_update: AlevelSubjectUpdate,
    db: Session = Depends(get_db)
):
    """更新 A-Level 科目信息"""
    updated = crud.update_alevel_subject(db, subject_id, subject_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"科目不存在 (ID: {subject_id})")
    return create_response(
        data=AlevelSubjectResponse.model_validate(updated).model_dump(),
        message="更新成功"
    )


@router.delete("/{subject_id}", response_model=SimpleResponse)
async def delete_alevel_subject(
    subject_id: int,
    db: Session = Depends(get_db)
):
    """删除 A-Level 科目"""
    success = crud.delete_alevel_subject(db, subject_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"科目不存在 (ID: {subject_id})")
    return SimpleResponse(code=200, message="删除成功", data=None)


# ── 导入导出 ───────────────────────────────────────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载 A-Level 科目导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "alevel_subjects_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "alevel_subjects_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_alevel_subjects(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入 A-Level 科目"""
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

    dup_errors = import_service.validate_unique_names(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在重复科目名称",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(dup_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in dup_errors],
            },
        }

    result = import_service.import_alevel_subjects_from_rows(db, rows)
    return create_import_response(result)
