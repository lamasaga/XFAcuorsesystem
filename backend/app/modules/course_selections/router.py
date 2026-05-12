"""
========================================
选课管理 API 路由
========================================

API 接口列表：
- GET    /api/v1/course-selections         获取选课记录列表
- GET    /api/v1/course-selections/{id}    获取单个选课详情
- POST   /api/v1/course-selections         创建选课记录
- PUT    /api/v1/course-selections/{id}    更新选课记录
- DELETE /api/v1/course-selections/{id}    删除选课记录
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
from app.modules.course_selections import crud
from app.modules.course_selections import service_import as import_service
from app.modules.course_selections.schemas import (
    CourseSelectionCreate,
    CourseSelectionUpdate,
    CourseSelectionResponse,
    CourseSelectionListResponse,
    SimpleResponse,
)

router = APIRouter()


@router.get("/", response_model=CourseSelectionListResponse)
async def get_course_selections(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量"),
    student_id: Optional[int] = Query(None, description="学生ID"),
    academic_year: Optional[str] = Query(None, description="学年"),
    semester: Optional[str] = Query(None, description="学期：FALL/SPRING"),
    status: Optional[str] = Query(None, description="状态"),
    db: Session = Depends(get_db)
):
    """获取选课记录列表"""
    skip = (page - 1) * page_size
    selections = crud.get_course_selections(
        db,
        skip=skip,
        limit=page_size,
        student_id=student_id,
        academic_year=academic_year,
        semester=semester,
        status=status
    )
    total = crud.get_course_selections_count(
        db,
        student_id=student_id,
        academic_year=academic_year,
        semester=semester,
        status=status
    )
    items = [CourseSelectionResponse.model_validate(s).model_dump() for s in selections]
    return create_pagination_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


# ── 导入导出 ── 必须在 /{selection_id} 之前注册 ──────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载选课导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "course_selections_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "course_selections_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_course_selections(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入选课记录"""
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

    result = import_service.import_selections_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{selection_id}", response_model=dict)
async def get_course_selection(
    selection_id: int,
    db: Session = Depends(get_db)
):
    """获取单个选课详情"""
    selection = crud.get_course_selection(db, selection_id)
    if not selection:
        raise HTTPException(status_code=404, detail=f"选课记录不存在 (ID: {selection_id})")
    return create_response(
        data=CourseSelectionResponse.model_validate(selection).model_dump()
    )


@router.post("/", response_model=dict)
async def create_course_selection(
    selection: CourseSelectionCreate,
    db: Session = Depends(get_db)
):
    """创建选课记录"""
    new_selection = crud.create_course_selection(db, selection)
    return create_response(
        data=CourseSelectionResponse.model_validate(new_selection).model_dump(),
        message="创建成功"
    )


@router.put("/{selection_id}", response_model=dict)
async def update_course_selection(
    selection_id: int,
    selection_update: CourseSelectionUpdate,
    db: Session = Depends(get_db)
):
    """更新选课记录"""
    updated = crud.update_course_selection(db, selection_id, selection_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"选课记录不存在 (ID: {selection_id})")
    return create_response(
        data=CourseSelectionResponse.model_validate(updated).model_dump(),
        message="更新成功"
    )


@router.delete("/{selection_id}", response_model=SimpleResponse)
async def delete_course_selection(
    selection_id: int,
    db: Session = Depends(get_db)
):
    """删除选课记录"""
    success = crud.delete_course_selection(db, selection_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"选课记录不存在 (ID: {selection_id})")
    return SimpleResponse(code=200, message="删除成功", data=None)
