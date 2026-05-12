"""
========================================
教学任务管理 API 路由
========================================
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.dependencies import get_db, create_response, create_pagination_response
from app.core.importer import create_import_response
from app.modules.tasks import crud
from app.modules.tasks.schemas import (
    TeachingTaskCreate,
    TeachingTaskUpdate,
    TeachingTaskResponse,
    TeachingTaskWithDetails
)
from app.modules.tasks import service_import as import_service

# 导入其他模块的 crud 用于验证
from app.modules.teachers.crud import get_teacher
from app.modules.classes.crud import get_class
from app.modules.subjects.crud import get_subject

router = APIRouter()


@router.get("/")
async def get_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    teacher_id: Optional[int] = Query(None, description="按教师过滤"),
    class_id: Optional[int] = Query(None, description="按班级过滤"),
    subject_id: Optional[int] = Query(None, description="按科目过滤"),
    db: Session = Depends(get_db)
):
    """获取教学任务列表"""
    skip = (page - 1) * page_size
    tasks = crud.get_tasks(
        db, skip=skip, limit=page_size,
        teacher_id=teacher_id, class_id=class_id, subject_id=subject_id
    )
    total = crud.get_tasks_count(
        db, teacher_id=teacher_id, class_id=class_id, subject_id=subject_id
    )
    items = [TeachingTaskResponse.model_validate(t).model_dump() for t in tasks]
    return create_pagination_response(items=items, total=total, page=page, page_size=page_size)


@router.get("/with-details")
async def get_tasks_with_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    class_id: Optional[int] = Query(None, description="按班级过滤"),
    grade: Optional[str] = Query(None, description="按年级过滤"),
    db: Session = Depends(get_db)
):
    """
    获取包含详细信息的教学任务列表
    
    返回的数据包含教师姓名、班级名称、科目名称等。
    """
    skip = (page - 1) * page_size
    tasks = crud.get_tasks_with_details(
        db, skip=skip, limit=page_size,
        class_id=class_id, grade=grade
    )
    total = len(tasks)  # 简化处理
    return create_pagination_response(items=tasks, total=total, page=page, page_size=page_size)


# ── 导入导出 ── 必须在 /{task_id} 之前注册 ─────────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载教学任务导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "tasks_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "tasks_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_tasks(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入教学任务"""
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

    result = import_service.import_tasks_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """获取单个教学任务"""
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"教学任务不存在 (ID: {task_id})")
    return create_response(data=TeachingTaskResponse.model_validate(task).model_dump())


@router.post("/")
async def create_task(task: TeachingTaskCreate, db: Session = Depends(get_db)):
    """
    创建教学任务
    
    会验证教师、班级、科目是否存在。
    """
    # 验证教师是否存在
    teacher = get_teacher(db, task.teacher_id)
    if not teacher:
        raise HTTPException(status_code=400, detail=f"教师不存在 (ID: {task.teacher_id})")
    
    # 验证班级是否存在
    class_ = get_class(db, task.class_id)
    if not class_:
        raise HTTPException(status_code=400, detail=f"班级不存在 (ID: {task.class_id})")
    
    # 验证科目是否存在
    subject = get_subject(db, task.subject_id)
    if not subject:
        raise HTTPException(status_code=400, detail=f"科目不存在 (ID: {task.subject_id})")
    
    # 检查任务是否已存在
    if crud.check_task_exists(db, task.teacher_id, task.class_id, task.subject_id):
        raise HTTPException(
            status_code=400,
            detail=f"该教学任务已存在（教师: {teacher.name}, 班级: {class_.name}, 科目: {subject.name}）"
        )
    
    new_task = crud.create_task(db, task)
    return create_response(
        data=TeachingTaskResponse.model_validate(new_task).model_dump(),
        message="创建成功"
    )


@router.post("/batch")
async def create_tasks_batch(tasks: List[TeachingTaskCreate], db: Session = Depends(get_db)):
    """批量创建教学任务"""
    # 批量验证教师、班级、科目是否存在
    teacher_ids = {t.teacher_id for t in tasks}
    class_ids = {t.class_id for t in tasks}
    subject_ids = {t.subject_id for t in tasks}
    
    missing = []
    for tid in teacher_ids:
        if not get_teacher(db, tid):
            missing.append(f"教师不存在 (ID: {tid})")
    for cid in class_ids:
        if not get_class(db, cid):
            missing.append(f"班级不存在 (ID: {cid})")
    for sid in subject_ids:
        if not get_subject(db, sid):
            missing.append(f"科目不存在 (ID: {sid})")
    
    if missing:
        raise HTTPException(status_code=400, detail="; ".join(missing))
    
    new_tasks = crud.create_tasks_batch(db, tasks)
    return create_response(
        data={"count": len(new_tasks)},
        message=f"成功创建 {len(new_tasks)} 个教学任务"
    )


@router.put("/{task_id}")
async def update_task(task_id: int, task_update: TeachingTaskUpdate, db: Session = Depends(get_db)):
    """更新教学任务"""
    # 如果更新了外键，验证关联数据
    if task_update.teacher_id and not get_teacher(db, task_update.teacher_id):
        raise HTTPException(status_code=400, detail=f"教师不存在 (ID: {task_update.teacher_id})")
    if task_update.class_id and not get_class(db, task_update.class_id):
        raise HTTPException(status_code=400, detail=f"班级不存在 (ID: {task_update.class_id})")
    if task_update.subject_id and not get_subject(db, task_update.subject_id):
        raise HTTPException(status_code=400, detail=f"科目不存在 (ID: {task_update.subject_id})")
    
    updated = crud.update_task(db, task_id, task_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"教学任务不存在 (ID: {task_id})")
    return create_response(
        data=TeachingTaskResponse.model_validate(updated).model_dump(),
        message="更新成功"
    )


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除教学任务"""
    success = crud.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"教学任务不存在 (ID: {task_id})")
    return create_response(message="删除成功")
