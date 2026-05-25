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


# ===========================================================
# 自动分班 API
# ===========================================================

@router.post("/allocate", response_model=dict)
async def allocate_course_classes(
    academic_year: str = Query("2025-2026", description="学年"),
    semester: str = Query("FALL", description="学期：FALL/SPRING"),
    min_students: int = Query(5, ge=1, description="最低开班人数"),
    db: Session = Depends(get_db)
):
    """
    自动分班算法
    
    根据已审批的选课记录，自动将学生分配到 A-Level 课程班。
    
    流程：
    1. 查询所有 APPROVED 状态的选课记录
    2. 按 A-Level 科目聚合学生
    3. 检查每个科目的学生数是否达到最低开班人数
    4. 按 max_capacity 拆分为平行班
    5. 均匀分配学生
    6. 创建 CourseClass 和 CourseClassMember 记录
    
    注意：
    - 如果某科目已有 ACTIVE 的课程班，会优先使用（在容量范围内补充学生）
    - 新创建的课程班 teacher_id 为空，需要管理员后续分配教师
    """
    from app.modules.course_selections.models import CourseSelection
    from app.modules.alevel_subjects.models import AlevelSubject
    from app.modules.course_classes.models import CourseClass, CourseClassMember
    from sqlalchemy import func
    import math
    
    # 1. 查询所有已审批的选课记录
    selections = db.query(CourseSelection).filter(
        CourseSelection.academic_year == academic_year,
        CourseSelection.semester == semester,
        CourseSelection.status == "APPROVED",
        CourseSelection.is_deleted == False,
    ).all()
    
    if not selections:
        return create_response(data={"created": 0, "details": []}, message="没有已审批的选课记录")
    
    # 2. 按 A-Level 科目聚合学生
    subject_students: dict[int, list[int]] = {}
    for sel in selections:
        for item in (sel.selections or []):
            subject_id = item.get("alevel_subject_id")
            if subject_id:
                subject_students.setdefault(subject_id, []).append(sel.student_id)
    
    # 去重（一个学生可能多次选同一科目）
    for subject_id in subject_students:
        subject_students[subject_id] = list(set(subject_students[subject_id]))
    
    # 3. 查询科目信息
    subject_ids = list(subject_students.keys())
    subjects = db.query(AlevelSubject).filter(
        AlevelSubject.id.in_(subject_ids),
        AlevelSubject.is_deleted == False,
    ).all()
    subject_map = {s.id: s for s in subjects}
    
    # 4. 查询现有课程班
    existing_classes = db.query(CourseClass).filter(
        CourseClass.academic_year == academic_year,
        CourseClass.semester == semester,
        CourseClass.status == "ACTIVE",
        CourseClass.is_deleted == False,
    ).all()
    
    # 按科目分组现有班级
    existing_by_subject: dict[int, list[CourseClass]] = {}
    for cc in existing_classes:
        existing_by_subject.setdefault(cc.alevel_subject_id, []).append(cc)
    
    # 5. 执行分班
    created_classes = []
    allocated_total = 0
    
    for subject_id, student_ids in subject_students.items():
        subject = subject_map.get(subject_id)
        if not subject:
            continue
        
        student_count = len(student_ids)
        if student_count < min_students:
            continue  # 不足最低开班人数
        
        max_capacity = subject.max_students or 20
        
        # 计算现有班级的剩余容量
        existing = existing_by_subject.get(subject_id, [])
        existing_capacity = 0
        for cc in existing:
            enrolled = db.query(func.count(CourseClassMember.id)).filter(
                CourseClassMember.course_class_id == cc.id,
                CourseClassMember.status == "ENROLLED",
            ).scalar() or 0
            existing_capacity += max(0, max_capacity - enrolled)
        
        # 如果现有班级容量足够，不需要新建
        if existing_capacity >= student_count:
            # 将学生分配到现有班级
            remaining_students = student_ids[:]
            for cc in existing:
                enrolled = db.query(func.count(CourseClassMember.id)).filter(
                    CourseClassMember.course_class_id == cc.id,
                    CourseClassMember.status == "ENROLLED",
                ).scalar() or 0
                available = max_capacity - enrolled
                if available <= 0:
                    continue
                to_add = remaining_students[:available]
                remaining_students = remaining_students[available:]
                
                for sid in to_add:
                    db.add(CourseClassMember(
                        course_class_id=cc.id,
                        student_id=sid,
                        status="ENROLLED",
                    ))
                allocated_total += len(to_add)
            
            created_classes.append({
                "subject_id": subject_id,
                "subject_name": subject.name,
                "student_count": student_count,
                "new_classes": 0,
                "existing_used": len(existing),
                "allocated": student_count,
            })
            continue
        
        # 需要新建班级
        # 先填满现有班级
        remaining_students = student_ids[:]
        for cc in existing:
            enrolled = db.query(func.count(CourseClassMember.id)).filter(
                CourseClassMember.course_class_id == cc.id,
                CourseClassMember.status == "ENROLLED",
            ).scalar() or 0
            available = max_capacity - enrolled
            if available <= 0:
                continue
            to_add = remaining_students[:available]
            remaining_students = remaining_students[available:]
            
            for sid in to_add:
                db.add(CourseClassMember(
                    course_class_id=cc.id,
                    student_id=sid,
                    status="ENROLLED",
                ))
            allocated_total += len(to_add)
        
        # 计算需要的新班数量
        new_count = math.ceil(len(remaining_students) / max_capacity)
        
        # 均匀分配学生到新班
        students_per_class = math.ceil(len(remaining_students) / new_count)
        
        for i in range(new_count):
            start = i * students_per_class
            end = min(start + students_per_class, len(remaining_students))
            class_students = remaining_students[start:end]
            
            if not class_students:
                continue
            
            # 创建新课程班（若科目有默认教师则自动带入）
            new_class = CourseClass(
                alevel_subject_id=subject_id,
                name=f"{subject.name} {i + 1}班",
                code=f"{subject.name[:3].upper()}{i+1}",
                max_capacity=max_capacity,
                current_enrollment=len(class_students),
                semester=semester,
                academic_year=academic_year,
                status="ACTIVE",
                teacher_id=subject.teacher_id,
            )
            db.add(new_class)
            db.flush()  # 获取 new_class.id
            
            # 添加成员
            for sid in class_students:
                db.add(CourseClassMember(
                    course_class_id=new_class.id,
                    student_id=sid,
                    status="ENROLLED",
                ))
            
            allocated_total += len(class_students)
            created_classes.append({
                "subject_id": subject_id,
                "subject_name": subject.name,
                "student_count": student_count,
                "new_class_id": new_class.id,
                "new_class_name": new_class.name,
                "class_size": len(class_students),
            })
    
    db.commit()
    
    return create_response(
        data={
            "academic_year": academic_year,
            "semester": semester,
            "total_subjects": len(subject_students),
            "allocated_students": allocated_total,
            "created_classes": created_classes,
        },
        message=f"自动分班完成，共分配 {allocated_total} 名学生"
    )
