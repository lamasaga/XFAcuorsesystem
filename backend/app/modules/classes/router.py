"""
========================================
班级管理 API 路由
========================================
"""

import re
import time
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.core.dependencies import get_db, create_response, create_pagination_response
from app.core.importer import create_import_response
from app.modules.classes import crud
from app.modules.classes.models import Class
from app.modules.classes.schemas import ClassCreate, ClassUpdate, ClassResponse, ClassPromoteRequest
from app.modules.classes import service_import as import_service

router = APIRouter()


def _parse_grade_from_name(name: str) -> Optional[str]:
    """从班级名称解析年级（容错处理）"""
    if not name:
        return None
    # 匹配 IPK-1, IKG-1, IG3-1, NG2-1 等格式
    match = re.match(r'[IN]?(PK|KG|G\d+)', name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _ensure_grade(cls_dict: dict) -> dict:
    """确保班级数据包含 grade 字段"""
    if not cls_dict.get('grade') and cls_dict.get('name'):
        cls_dict['grade'] = _parse_grade_from_name(cls_dict['name'])
    return cls_dict


def _fix_deleted_class_name(db: Session, name: str) -> bool:
    """
    修复已软删除但未重命名的班级记录
    
    如果存在同名但已删除的班级，将其重命名以释放名称。
    这是为了兼容旧版本软删除逻辑产生的历史数据。
    
    Returns:
        True 如果进行了修复，False 如果无需修复
    """
    # 查找同名但已删除的记录
    deleted_class = db.query(Class).filter(
        Class.name == name,
        Class.is_deleted == True
    ).first()
    
    if deleted_class:
        # 重命名已删除的记录，释放原名称
        # 使用 "_D[ID]" 格式，确保不超过 20 字符且唯一
        deleted_class.name = f"_D{deleted_class.id}"
        db.commit()
        return True
    return False


@router.get("/")
async def get_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    type: Optional[str] = Query(None, description="班级类型：I/N"),
    department: Optional[str] = Query(None, description="学部"),
    grade: Optional[str] = Query(None, description="年级"),
    db: Session = Depends(get_db)
):
    """获取班级列表"""
    skip = (page - 1) * page_size
    classes = crud.get_classes(db, skip=skip, limit=page_size, type=type, department=department, grade=grade)
    total = crud.get_classes_count(db, type=type, department=department, grade=grade)
    # 确保每个班级都有 grade 字段（从名称解析作为容错）
    items = [_ensure_grade(ClassResponse.model_validate(c).model_dump()) for c in classes]
    return create_pagination_response(items=items, total=total, page=page, page_size=page_size)


# ── 导入导出 ── 必须在 /{class_id} 之前注册 ───────────

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载班级导入模板"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "classes_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "classes_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_classes(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入班级"""
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

    dup_errors = import_service.validate_unique_classes(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在重复班级名称",
            "data": {
                "created": 0, "updated": 0, "skipped": 0,
                "failed": len(dup_errors),
                "errors": [{"rowNumber": e.row_number, "identifier": e.identifier, "message": e.message} for e in dup_errors],
            },
        }

    result = import_service.import_classes_from_rows(db, rows)
    return create_import_response(result)


@router.get("/{class_id}")
async def get_class(class_id: int, db: Session = Depends(get_db)):
    """获取单个班级"""
    cls = crud.get_class(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail=f"班级不存在 (ID: {class_id})")
    return create_response(data=_ensure_grade(ClassResponse.model_validate(cls).model_dump()))


@router.post("/")
async def create_class(class_data: ClassCreate, db: Session = Depends(get_db)):
    """创建班级"""
    # 检查名称是否重复（只检查未删除的）
    existing = crud.get_class_by_name(db, class_data.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"班级名称已存在: {class_data.name}")
    
    try:
        new_class = crud.create_class(db, class_data)
        return create_response(data=ClassResponse.model_validate(new_class).model_dump(), message="创建成功")
    except IntegrityError as e:
        db.rollback()
        # 处理数据库唯一约束冲突
        if "classes_name_key" in str(e):
            # 尝试自动修复：可能是旧版本软删除的记录没有重命名
            if _fix_deleted_class_name(db, class_data.name):
                # 修复成功，重试创建
                try:
                    new_class = crud.create_class(db, class_data)
                    return create_response(data=ClassResponse.model_validate(new_class).model_dump(), message="创建成功")
                except IntegrityError:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=f"班级名称已存在: {class_data.name}")
            raise HTTPException(status_code=400, detail=f"班级名称已存在: {class_data.name}")
        raise HTTPException(status_code=400, detail="数据冲突，请检查输入")


@router.put("/{class_id}")
async def update_class(class_id: int, class_update: ClassUpdate, db: Session = Depends(get_db)):
    """更新班级"""
    updated = crud.update_class(db, class_id, class_update)
    if not updated:
        raise HTTPException(status_code=404, detail=f"班级不存在 (ID: {class_id})")
    return create_response(data=ClassResponse.model_validate(updated).model_dump(), message="更新成功")


@router.delete("/{class_id}")
async def delete_class(class_id: int, db: Session = Depends(get_db)):
    """删除班级"""
    success = crud.delete_class(db, class_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"班级不存在 (ID: {class_id})")
    return create_response(message="删除成功")


# ── 一键升班 ───────────────────────────────────────────

# 年级排序（用于升班逻辑）
GRADE_ORDER = ['PK', 'KG', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12']
GRADE_NEXT = {GRADE_ORDER[i]: GRADE_ORDER[i + 1] for i in range(len(GRADE_ORDER) - 1)}


def _get_department_by_grade(grade: str) -> str:
    """根据年级判断学部"""
    if grade in ('PK', 'KG', 'G1', 'G2', 'G3', 'G4', 'G5'):
        return 'PRIMARY'
    return 'SECONDARY'


@router.post("/promote", response_model=dict)
async def promote_classes(request: ClassPromoteRequest, db: Session = Depends(get_db)):
    """
    一键升班
    
    将指定年级的所有班级升级到下一年级：
    - 班级名称中的年级部分自动更新（如 IG3-1 → IG4-1）
    - 班级年级自动递增
    - 学部根据新年级自动调整
    - 该班级下的所有学生年级同步更新
    - G12 班级会标记为毕业（学生状态设为 GRADUATED）
    """
    from app.modules.students.models import Student
    import re

    # 确定要处理的年级
    source_grades = request.grades
    if not source_grades:
        # 默认升级所有非毕业年级
        source_grades = GRADE_ORDER[:-1]  # 排除 G12

    promoted_classes = []
    failed_classes = []
    graduated_count = 0

    for old_grade in source_grades:
        if old_grade not in GRADE_NEXT:
            continue  # G12 或未知年级跳过

        new_grade = GRADE_NEXT[old_grade]
        classes = db.query(Class).filter(
            Class.grade == old_grade,
            Class.is_deleted == False
        ).all()

        for cls in classes:
            # 生成新名称：将旧年级替换为新年级的年级
            # 例如 IG3-1 → IG4-1, NG2-1 → NG3-1, PKG-1 → PKG1-1（实际上PK→KG是PK-1→KG-1）
            old_pattern = re.escape(old_grade)
            new_name = re.sub(old_pattern, new_grade, cls.name, count=1, flags=re.IGNORECASE)

            # 检查新名称是否已存在
            existing = db.query(Class).filter(
                Class.name == new_name,
                Class.is_deleted == False,
                Class.id != cls.id
            ).first()

            if existing:
                failed_classes.append({
                    "class_id": cls.id,
                    "old_name": cls.name,
                    "new_name": new_name,
                    "reason": f"目标名称 '{new_name}' 已存在"
                })
                continue

            # 保存旧名称（在修改前捕获）
            old_name = cls.name

            # 更新班级
            cls.name = new_name
            cls.grade = new_grade
            cls.department = _get_department_by_grade(new_grade)

            # 统计该班级学生数并更新学生年级
            students = db.query(Student).filter(
                Student.class_id == cls.id,
                Student.is_deleted == False
            ).all()
            student_count = len(students)

            for student in students:
                student.grade = new_grade

            promoted_classes.append({
                "class_id": cls.id,
                "old_name": old_name,
                "new_name": new_name,
                "old_grade": old_grade,
                "new_grade": new_grade,
                "student_count": student_count
            })

    db.commit()

    # 处理 G12 毕业（如果 source_grades 包含 G12）
    if 'G12' in source_grades:
        g12_classes = db.query(Class).filter(
            Class.grade == 'G12',
            Class.is_deleted == False
        ).all()
        for cls in g12_classes:
            # 将 G12 学生标记为毕业
            graduated = db.query(Student).filter(
                Student.class_id == cls.id,
                Student.is_deleted == False,
                Student.status != 'GRADUATED'
            ).update({Student.status: 'GRADUATED'}, synchronize_session=False)
            graduated_count += graduated

        db.commit()

    return create_response(
        message=f"升班完成：成功升级 {len(promoted_classes)} 个班级"
                f"{'，毕业 ' + str(graduated_count) + ' 人' if graduated_count else ''}"
                f"{'，失败 ' + str(len(failed_classes)) + ' 个' if failed_classes else ''}",
        data={
            "promoted": promoted_classes,
            "failed": failed_classes,
            "graduated_count": graduated_count
        }
    )
