from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.core.dependencies import get_db
from app.core.importer import create_import_response
from . import schemas, crud, models
from . import service_import as import_service
from app.modules.tasks.models import TeachingTask
from app.modules.classes.models import Class as ClassModel

router = APIRouter(
    tags=["分层/合班课程 (Layer & Combine Courses)"]
)


def _sync_layer_tasks(db: Session, layer_group: models.LayerGroup):
    """
    同步分层/合班课程的教学任务
    
    根据课程类型自动创建教学任务：
    - LAYER（分层）：为涉及年级的所有班级创建 Task，教师轮流分配
    - COMBINE（合班）：为指定的班级创建 Task，使用同一个教师
    
    这确保了排课时能正确锁定所有涉及班级的时间。
    """
    # 删除该分层组原有的所有教学任务
    db.query(TeachingTask).filter(
        TeachingTask.layer_group_id == layer_group.id,
        TeachingTask.is_deleted == False
    ).update({"is_deleted": True})
    
    # 如果没有配置教师，则不创建任务
    teacher_ids = layer_group.teacher_ids or []
    if not teacher_ids:
        db.commit()
        return
    
    # 根据课程类型获取涉及的班级
    group_type = layer_group.group_type or "LAYER"
    target_classes = []
    class_ids = layer_group.class_ids or []
    
    if class_ids:
        # 优先使用 class_ids（无论 LAYER 还是 COMBINE 模式）
        target_classes = db.query(ClassModel).filter(
            ClassModel.id.in_(class_ids),
            ClassModel.is_deleted == False
        ).all()
    elif group_type == "COMBINE":
        # 合班模式但 class_ids 为空 → 无法创建任务
        pass
    else:
        # 分层模式且 class_ids 为空（兼容旧数据）：按 grades 查询
        grades = layer_group.grades or []
        if grades:
            target_classes = db.query(ClassModel).filter(
                ClassModel.grade.in_(grades),
                ClassModel.is_deleted == False
            ).all()
            
            # 如果通过 grade 字段没找到，尝试从班级名称解析
            if not target_classes:
                from sqlalchemy import or_
                conditions = [ClassModel.name.contains(g) for g in grades]
                target_classes = db.query(ClassModel).filter(
                    or_(*conditions),
                    ClassModel.is_deleted == False
                ).all()
    
    if not target_classes:
        db.commit()
        return
    
    # 为每个班级创建教学任务
    for idx, cls in enumerate(target_classes):
        if group_type == "COMBINE":
            # 合班模式：所有班级使用同一个教师
            teacher_id = teacher_ids[0] if teacher_ids else None
            note = f"合班课程 - {cls.name}"
        else:
            # 分层模式：教师轮流分配给不同班级
            teacher_idx = idx % len(teacher_ids)
            teacher_id = teacher_ids[teacher_idx]
            layer_num = teacher_idx + 1
            note = f"分层课程第{layer_num}层 - {cls.name}"
        
        if not teacher_id or teacher_id <= 0:
            continue
        
        # 创建教学任务
        task = TeachingTask(
            teacher_id=teacher_id,
            class_id=cls.id,
            subject_id=layer_group.subject_id,
            weekly_hours=layer_group.weekly_hours,
            is_continuous=layer_group.needs_continuous,
            continuous_count=2 if layer_group.needs_continuous else 1,
            layer_group_id=layer_group.id,
            note=note
        )
        db.add(task)
    
    db.commit()


def serialize_layer_group(group: models.LayerGroup) -> dict:
    """将 LayerGroup ORM 对象转换为字典"""
    return schemas.LayerGroupResponse.model_validate(group).model_dump()


@router.get("/", response_model=dict)
def read_layer_groups(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    db: Session = Depends(get_db)
):
    """获取分层组列表"""
    skip = (page - 1) * page_size
    groups = crud.get_layer_groups(db, skip=skip, limit=page_size)
    # 获取真实总数
    total = db.query(func.count(models.LayerGroup.id)).scalar()
    # 序列化所有分层组
    items = [serialize_layer_group(g) for g in groups]
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


# ── 导入导出 ── 必须在 /{group_id} 之前注册 ───────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载分层课程导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "layers_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "layers_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_layers(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入分层/合班课程"""
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

    result = import_service.import_layers_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{group_id}", response_model=dict)
def read_layer_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """获取单个分层组详情"""
    group = crud.get_layer_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分层组不存在")
    return {
        "code": 200,
        "message": "success",
        "data": serialize_layer_group(group)
    }


@router.post("/", response_model=dict)
def create_layer_group(
    group: schemas.LayerGroupCreate, 
    db: Session = Depends(get_db)
):
    """创建分层课程"""
    new_group = crud.create_layer_group(db, group=group)
    
    # 自动同步教学任务
    _sync_layer_tasks(db, new_group)
    
    return {
        "code": 200,
        "message": "success",
        "data": serialize_layer_group(new_group)
    }


@router.put("/{group_id}", response_model=dict)
def update_layer_group(
    group_id: int,
    group_update: schemas.LayerGroupUpdate,
    db: Session = Depends(get_db)
):
    """更新分层课程"""
    updated_group = crud.update_layer_group(db, group_id, group_update)
    if not updated_group:
        raise HTTPException(status_code=404, detail="分层课程不存在")
    
    # 重新同步教学任务
    _sync_layer_tasks(db, updated_group)
    
    return {
        "code": 200,
        "message": "success",
        "data": serialize_layer_group(updated_group)
    }


@router.delete("/{group_id}", response_model=dict)
def delete_layer_group(
    group_id: int, 
    db: Session = Depends(get_db)
):
    """删除分层/合班课程"""
    # 检查是否存在
    group = crud.get_layer_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分层/合班课程不存在")
    
    # 先断开关联的教学任务的外键引用，并软删除
    db.query(TeachingTask).filter(
        TeachingTask.layer_group_id == group_id
    ).update({
        "layer_group_id": None,  # 断开外键引用
        "is_deleted": True
    })
    db.commit()
    
    # 再删除分层/合班课程
    deleted = crud.delete_layer_group(db, group_id)
    return {"code": 200, "message": "success"}
