"""
========================================
学生管理 API 路由
========================================

API 接口列表：
- GET    /api/v1/students         获取学生列表
- GET    /api/v1/students/{id}    获取单个学生详情
- POST   /api/v1/students         创建新学生
- PUT    /api/v1/students/{id}    更新学生信息
- DELETE /api/v1/students/{id}    删除学生
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
from app.modules.students import crud
from app.modules.students.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentListResponse,
    SimpleResponse,
    StudentPromoteRequest,
)
from app.modules.students import service_import as import_service

router = APIRouter()


@router.get("/", response_model=StudentListResponse)
async def get_students(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量"),
    grade: Optional[str] = Query(None, description="年级：G10-G12"),
    status: Optional[str] = Query(None, description="状态"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取学生列表"""
    skip = (page - 1) * page_size
    students = crud.get_students(
        db,
        skip=skip,
        limit=page_size,
        grade=grade,
        status=status,
        search=search
    )
    total = crud.get_students_count(
        db,
        grade=grade,
        status=status,
        search=search
    )
    items = [StudentResponse.model_validate(s).model_dump() for s in students]
    return create_pagination_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


# ── 导入导出 ── 必须在 /{student_id} 之前注册 ─────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载学生导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "students_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "students_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_students(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入学生"""
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

    dup_errors = import_service.validate_unique_students(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在重复学号",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(dup_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in dup_errors],
            },
        }

    result = import_service.import_students_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{student_id}", response_model=dict)
async def get_student(
    student_id: int,
    db: Session = Depends(get_db)
):
    """获取单个学生详情"""
    student = crud.get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"学生不存在 (ID: {student_id})")
    return create_response(
        data=StudentResponse.model_validate(student).model_dump()
    )


@router.post("/", response_model=dict)
async def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db)
):
    """创建新学生"""
    # 检查学号是否已存在
    existing = crud.get_student_by_no(db, student.student_no)
    if existing:
        raise HTTPException(status_code=400, detail="学号已存在")
    
    new_student = crud.create_student(db, student)
    return create_response(
        data=StudentResponse.model_validate(new_student).model_dump(),
        message="创建成功"
    )


@router.put("/{student_id}", response_model=dict)
async def update_student(
    student_id: int,
    student_update: StudentUpdate,
    db: Session = Depends(get_db)
):
    """更新学生信息"""
    # 如果更新学号，检查是否与其他学生冲突
    if student_update.student_no:
        existing = crud.get_student_by_no(db, student_update.student_no)
        if existing and existing.id != student_id:
            raise HTTPException(status_code=400, detail="学号已存在")
    
    updated = crud.update_student(db, student_id, student_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"学生不存在 (ID: {student_id})")
    return create_response(
        data=StudentResponse.model_validate(updated).model_dump(),
        message="更新成功"
    )


@router.delete("/{student_id}", response_model=SimpleResponse)
async def delete_student(
    student_id: int,
    db: Session = Depends(get_db)
):
    """删除学生"""
    success = crud.delete_student(db, student_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"学生不存在 (ID: {student_id})")
    return SimpleResponse(code=200, message="删除成功", data=None)

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载学生导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "students_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "students_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_students(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入学生"""
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

    dup_errors = import_service.validate_unique_students(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在重复学号",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(dup_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in dup_errors],
            },
        }

    result = import_service.import_students_from_rows(db, rows)
    return create_import_response(result)


# ── 一键升年级 ───────────────────────────────────────────

STUDENT_GRADE_ORDER = ['PK', 'KG', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12']
STUDENT_GRADE_NEXT = {STUDENT_GRADE_ORDER[i]: STUDENT_GRADE_ORDER[i + 1] for i in range(len(STUDENT_GRADE_ORDER) - 1)}


@router.post("/promote", response_model=dict)
async def promote_students(request: StudentPromoteRequest, db: Session = Depends(get_db)):
    """
    一键升年级

    将指定年级的在读学生升级到下一年级：
    - G10 → G11
    - G11 → G12
    - G12 → GRADUATED（毕业）
    - 其他年级同理（PK→KG→G1→...→G12）
    """
    from app.modules.students.models import Student

    source_grades = request.grades
    if not source_grades:
        # 默认升级所有非毕业在读学生
        source_grades = [g for g in STUDENT_GRADE_ORDER if g != 'G12']

    promoted = 0
    graduated = 0
    errors = []

    for old_grade in source_grades:
        if old_grade not in STUDENT_GRADE_NEXT:
            continue  # G12 或未知年级

        new_grade = STUDENT_GRADE_NEXT[old_grade]
        students = db.query(Student).filter(
            Student.grade == old_grade,
            Student.status == 'ACTIVE',
            Student.is_deleted == False
        ).all()

        for student in students:
            student.grade = new_grade
            promoted += 1

    # 处理 G12 毕业
    if 'G12' in source_grades:
        g12_graduated = db.query(Student).filter(
            Student.grade == 'G12',
            Student.status == 'ACTIVE',
            Student.is_deleted == False
        ).update({Student.status: 'GRADUATED'}, synchronize_session=False)
        graduated += g12_graduated

    db.commit()

    return create_response(
        message=f"升年级完成：升级 {promoted} 人"
                f"{'，毕业 ' + str(graduated) + ' 人' if graduated else ''}",
        data={"promoted": promoted, "graduated": graduated, "errors": errors}
    )
