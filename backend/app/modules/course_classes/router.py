"""
========================================
课程班管理 API 路由
========================================

API 接口列表：
- GET    /api/v1/course-classes              获取课程班列表
- GET    /api/v1/course-classes/{id}         获取单个课程班详情
- POST   /api/v1/course-classes              创建课程班
- PUT    /api/v1/course-classes/{id}         更新课程班
- DELETE /api/v1/course-classes/{id}         删除课程班
- GET    /api/v1/course-classes/{id}/members 获取课程班成员
- POST   /api/v1/course-classes/{id}/members 添加课程班成员
- DELETE /api/v1/course-classes/members/{id} 移除课程班成员
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
from app.modules.course_classes import crud
from app.modules.course_classes import service_import as import_service
from app.modules.course_classes.schemas import (
    CourseClassCreate,
    CourseClassUpdate,
    CourseClassResponse,
    CourseClassListResponse,
    CourseClassMemberCreate,
    CourseClassMemberResponse,
    SimpleResponse,
)

router = APIRouter()


@router.get("/", response_model=CourseClassListResponse)
async def get_course_classes(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量"),
    alevel_subject_id: Optional[int] = Query(None, description="A-Level 科目ID"),
    teacher_id: Optional[int] = Query(None, description="教师ID"),
    semester: Optional[str] = Query(None, description="学期"),
    academic_year: Optional[str] = Query(None, description="学年"),
    status: Optional[str] = Query(None, description="状态"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取课程班列表"""
    skip = (page - 1) * page_size
    classes = crud.get_course_classes(
        db,
        skip=skip,
        limit=page_size,
        alevel_subject_id=alevel_subject_id,
        teacher_id=teacher_id,
        semester=semester,
        academic_year=academic_year,
        status=status,
        search=search
    )
    total = crud.get_course_classes_count(
        db,
        alevel_subject_id=alevel_subject_id,
        teacher_id=teacher_id,
        semester=semester,
        academic_year=academic_year,
        status=status,
        search=search
    )
    items = [CourseClassResponse.model_validate(c).model_dump() for c in classes]
    return create_pagination_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


# ── 导入导出 ── 必须在 /{class_id} 之前注册 ───────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载课程班导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "course_classes_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "course_classes_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_course_classes(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入课程班"""
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

    result = import_service.import_course_classes_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{class_id}", response_model=dict)
async def get_course_class(
    class_id: int,
    db: Session = Depends(get_db)
):
    """获取单个课程班详情"""
    course_class = crud.get_course_class(db, class_id)
    if not course_class:
        raise HTTPException(status_code=404, detail=f"课程班不存在 (ID: {class_id})")
    return create_response(
        data=CourseClassResponse.model_validate(course_class).model_dump()
    )


@router.post("/", response_model=dict)
async def create_course_class(
    course_class: CourseClassCreate,
    db: Session = Depends(get_db)
):
    """创建课程班"""
    new_class = crud.create_course_class(db, course_class)
    return create_response(
        data=CourseClassResponse.model_validate(new_class).model_dump(),
        message="创建成功"
    )


@router.put("/{class_id}", response_model=dict)
async def update_course_class(
    class_id: int,
    class_update: CourseClassUpdate,
    db: Session = Depends(get_db)
):
    """更新课程班信息"""
    updated = crud.update_course_class(db, class_id, class_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"课程班不存在 (ID: {class_id})")
    return create_response(
        data=CourseClassResponse.model_validate(updated).model_dump(),
        message="更新成功"
    )


@router.delete("/{class_id}", response_model=SimpleResponse)
async def delete_course_class(
    class_id: int,
    db: Session = Depends(get_db)
):
    """删除课程班"""
    success = crud.delete_course_class(db, class_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"课程班不存在 (ID: {class_id})")
    return SimpleResponse(code=200, message="删除成功", data=None)


# ========== 课程班成员管理 ==========

@router.get("/{class_id}/members", response_model=dict)
async def get_course_class_members(
    class_id: int,
    db: Session = Depends(get_db)
):
    """获取课程班成员列表"""
    members = crud.get_course_class_members(db, class_id)
    items = [CourseClassMemberResponse.model_validate(m).model_dump() for m in members]
    return create_response(data={"items": items, "total": len(items)})


@router.post("/{class_id}/members", response_model=dict)
async def add_course_class_member(
    class_id: int,
    member: CourseClassMemberCreate,
    db: Session = Depends(get_db)
):
    """添加课程班成员"""
    # 确保 course_class_id 一致
    member_data = CourseClassMemberCreate(
        course_class_id=class_id,
        student_id=member.student_id,
        status=member.status
    )
    new_member = crud.add_course_class_member(db, member_data)
    return create_response(
        data=CourseClassMemberResponse.model_validate(new_member).model_dump(),
        message="添加成功"
    )


@router.delete("/members/{member_id}", response_model=SimpleResponse)
async def remove_course_class_member(
    member_id: int,
    db: Session = Depends(get_db)
):
    """移除课程班成员"""
    success = crud.remove_course_class_member(db, member_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"成员不存在 (ID: {member_id})")
    return SimpleResponse(code=200, message="移除成功", data=None)
