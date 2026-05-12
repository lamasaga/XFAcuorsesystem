"""
========================================
教师管理 API 路由
========================================

这个文件定义了教师管理的所有 API 接口。

API 接口列表：
- GET    /api/v1/teachers         获取教师列表（支持分页、搜索、过滤）
- GET    /api/v1/teachers/{id}    获取单个教师详情
- POST   /api/v1/teachers         创建新教师
- PUT    /api/v1/teachers/{id}    更新教师信息
- DELETE /api/v1/teachers/{id}    删除教师

FastAPI 路由装饰器说明：
- @router.get("/path"): 处理 GET 请求
- @router.post("/path"): 处理 POST 请求
- @router.put("/path"): 处理 PUT 请求
- @router.delete("/path"): 处理 DELETE 请求

参数来源：
- 路径参数：从 URL 中提取，如 /teachers/{id} 中的 id
- 查询参数：从 URL 查询字符串提取，如 ?page=1&limit=10
- 请求体：从 HTTP 请求体中提取，通常是 JSON

使用方法：
    # 这个路由会在 main.py 中被注册
    from app.modules.teachers.router import router as teachers_router
    app.include_router(teachers_router, prefix="/api/v1/teachers")
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# APIRouter: 用于创建路由组
# Depends: 依赖注入
# HTTPException: HTTP 异常
# Query: 查询参数装饰器
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

# Session: SQLAlchemy 会话类型
from sqlalchemy.orm import Session

# List, Optional: 类型提示
from typing import List, Optional

# 导入数据库会话依赖
from app.core.dependencies import (
    get_db,
    create_response,
    create_pagination_response
)

# 导入 CRUD 操作和模式
from app.modules.teachers import crud
from app.modules.teachers.schemas import (
    TeacherCreate,
    TeacherUpdate,
    TeacherResponse,
    TeacherListResponse,
    SimpleResponse,
    ResearchGroupCreate,
    ResearchGroupResponse,
)
from app.modules.teachers.models import ResearchGroup
from app.modules.teachers import service_import as import_service


# -----------------------------------------
# 创建路由器
# -----------------------------------------
# APIRouter 类似于 Flask 的 Blueprint
# 它可以将多个相关的路由组织在一起
router = APIRouter()

@router.get("/import/template", response_model=None)
async def download_import_template(format: str = Query("xlsx", description="模板格式：xlsx/csv")):
    """下载教师导入模板（xlsx/csv）"""
    fmt = (format or "xlsx").lower()
    if fmt not in {"xlsx", "csv"}:
        raise HTTPException(status_code=400, detail="format 仅支持 xlsx 或 csv")

    if fmt == "xlsx":
        content = import_service.build_template_xlsx()
        filename = "teachers_import_template.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = import_service.build_template_csv()
        filename = "teachers_import_template.csv"
        media_type = "text/csv; charset=utf-8"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=dict)
async def import_teachers(
    file: UploadFile = File(..., description="xlsx/csv 文件"),
    db: Session = Depends(get_db),
):
    """批量导入教师（xlsx/csv）"""
    content = await file.read()
    rows, parse_errors = import_service.parse_import_file(file.filename or "", content)
    if parse_errors:
        return {
            "code": 400,
            "message": "导入失败：文件解析错误",
            "data": {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "failed": len(parse_errors),
                "errors": [e.__dict__ for e in parse_errors],
            },
        }

    dup_errors = import_service.validate_duplicate_names(rows)
    if dup_errors:
        return {
            "code": 400,
            "message": "导入失败：存在未处理的重名",
            "data": {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "failed": len(dup_errors),
                "errors": [e.__dict__ for e in dup_errors],
            },
        }

    result = import_service.import_teachers_from_rows(db, rows)
    return {
        "code": 200,
        "message": "导入完成" if result.failed == 0 else "导入完成（部分失败）",
        "data": {
            "created": result.created,
            "updated": result.updated,
            "skipped": result.skipped,
            "failed": result.failed,
            "errors": [e.__dict__ for e in result.errors],
        },
    }


# -----------------------------------------
# 教研组管理
# -----------------------------------------
@router.get("/research-groups", response_model=dict)
async def get_research_groups(db: Session = Depends(get_db)):
    """获取所有教研组"""
    groups = db.query(ResearchGroup).filter(
        ResearchGroup.is_deleted == False
    ).order_by(ResearchGroup.id).all()
    items = [ResearchGroupResponse.model_validate(g).model_dump() for g in groups]
    return {"code": 200, "message": "success", "data": {"items": items}}


@router.post("/research-groups", response_model=dict)
async def create_research_group(
    payload: ResearchGroupCreate,
    db: Session = Depends(get_db)
):
    """创建教研组"""
    exists = db.query(ResearchGroup).filter(
        ResearchGroup.name == payload.name,
        ResearchGroup.is_deleted == False,
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="教研组名称已存在")
    group = ResearchGroup(name=payload.name)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {
        "code": 200,
        "message": "创建成功",
        "data": ResearchGroupResponse.model_validate(group).model_dump(),
    }


@router.delete("/research-groups/{group_id}", response_model=dict)
async def delete_research_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """删除教研组（软删除，并解除教师关联）"""
    group = db.query(ResearchGroup).filter(
        ResearchGroup.id == group_id,
        ResearchGroup.is_deleted == False,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="教研组不存在")
    group.is_deleted = True
    # 解除所有关联教师
    from app.modules.teachers.models import Teacher
    db.query(Teacher).filter(
        Teacher.research_group_id == group_id
    ).update({"research_group_id": None})
    db.commit()
    return {"code": 200, "message": "删除成功", "data": None}


# -----------------------------------------
# 获取教师列表
# -----------------------------------------
@router.get("/", response_model=TeacherListResponse)
async def get_teachers(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量"),
    type: Optional[str] = Query(None, description="教师类型：CN/EN"),
    department: Optional[str] = Query(None, description="学部：PRIMARY/SECONDARY"),
    search: Optional[str] = Query(None, description="搜索关键词（姓名）"),
    db: Session = Depends(get_db)
):
    """
    获取教师列表
    
    支持分页、搜索和过滤功能。
    
    **请求参数**（查询字符串）:
    - page: 页码，默认 1
    - page_size: 每页数量，默认 20
    - type: 教师类型过滤，可选值 CN（中教）、EN（外教）
    - department: 学部过滤，可选值 PRIMARY（小学部）、SECONDARY（中学部）
    - search: 搜索关键词，按教师姓名模糊搜索
    
    **响应示例**:
    ```json
    {
        "code": 200,
        "message": "success",
        "data": {
            "items": [
                {
                    "id": 1,
                    "name": "张三",
                    "type": "CN",
                    "department": "PRIMARY",
                    "subjects": ["语文"],
                    "tags": ["HOMEROOM_TEACHER"],
                    "max_weekly_hours": 25,
                    "weekly_hours": 18
                }
            ],
            "total": 50,
            "page": 1,
            "page_size": 20,
            "pages": 3
        }
    }
    ```
    
    Args:
        page: 页码
        page_size: 每页数量
        type: 教师类型过滤
        department: 学部过滤
        search: 搜索关键词
        db: 数据库会话（自动注入）
    
    Returns:
        TeacherListResponse: 教师列表响应
    """
    # 计算跳过的记录数
    skip = (page - 1) * page_size
    
    # 获取教师列表
    teachers = crud.get_teachers(
        db,
        skip=skip,
        limit=page_size,
        type=type,
        department=department,
        search=search
    )
    
    # 获取总数
    total = crud.get_teachers_count(
        db,
        type=type,
        department=department,
        search=search
    )
    
    # 将 ORM 对象转换为字典列表
    items = [TeacherResponse.model_validate(t).model_dump() for t in teachers]
    
    # 返回分页响应
    return create_pagination_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


# -----------------------------------------
# 获取单个教师
# -----------------------------------------
@router.get("/{teacher_id}", response_model=dict)
async def get_teacher(
    teacher_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个教师详情
    
    根据教师 ID 获取教师的完整信息。
    
    **路径参数**:
    - teacher_id: 教师 ID
    
    **响应示例**:
    ```json
    {
        "code": 200,
        "message": "success",
        "data": {
            "id": 1,
            "name": "张三",
            "type": "CN",
            "department": "PRIMARY",
            "subjects": ["语文", "数学"],
            "tags": ["HOMEROOM_TEACHER"],
            "max_weekly_hours": 25,
            "weekly_hours": 18,
            "unavailable_slots": {"1": [1, 2]},
            "created_at": "2024-01-01T00:00:00"
        }
    }
    ```
    
    Args:
        teacher_id: 教师 ID（路径参数）
        db: 数据库会话
    
    Returns:
        dict: 教师详情响应
    
    Raises:
        HTTPException: 404 - 教师不存在
    """
    # 查询教师
    teacher = crud.get_teacher(db, teacher_id)
    
    # 如果不存在，返回 404 错误
    if not teacher:
        raise HTTPException(
            status_code=404,
            detail=f"教师不存在 (ID: {teacher_id})"
        )
    
    # 返回成功响应
    return create_response(
        data=TeacherResponse.model_validate(teacher).model_dump()
    )


# -----------------------------------------
# 创建教师
# -----------------------------------------
@router.post("/", response_model=dict)
async def create_teacher(
    teacher: TeacherCreate,
    db: Session = Depends(get_db)
):
    """
    创建新教师
    
    **请求体**:
    ```json
    {
        "name": "张三",
        "type": "CN",
        "department": "PRIMARY",
        "subjects": ["语文", "数学"],
        "tags": ["HOMEROOM_TEACHER"],
        "max_weekly_hours": 25
    }
    ```
    
    **字段说明**:
    - name: 教师姓名（必填）
    - type: 教师类型，CN=中教，EN=外教（默认 CN）
    - department: 学部，PRIMARY=小学部，SECONDARY=中学部（默认 PRIMARY）
    - subjects: 任教科目列表（默认空列表）
    - tags: 标签列表，如 HOMEROOM_TEACHER 表示班主任
    - max_weekly_hours: 每周最大课时数（默认 25）
    
    **响应示例**:
    ```json
    {
        "code": 200,
        "message": "创建成功",
        "data": {
            "id": 1,
            "name": "张三",
            ...
        }
    }
    ```
    
    Args:
        teacher: 教师创建数据（请求体）
        db: 数据库会话
    
    Returns:
        dict: 创建成功响应
    """
    # 创建教师
    new_teacher = crud.create_teacher(db, teacher)
    
    # 返回成功响应
    return create_response(
        data=TeacherResponse.model_validate(new_teacher).model_dump(),
        message="创建成功"
    )


# -----------------------------------------
# 更新教师
# -----------------------------------------
@router.put("/{teacher_id}", response_model=dict)
async def update_teacher(
    teacher_id: int,
    teacher_update: TeacherUpdate,
    db: Session = Depends(get_db)
):
    """
    更新教师信息
    
    只需要传入要更新的字段，未传入的字段保持不变。
    
    **路径参数**:
    - teacher_id: 教师 ID
    
    **请求体**（所有字段可选）:
    ```json
    {
        "name": "李四",
        "subjects": ["英语"]
    }
    ```
    
    **响应示例**:
    ```json
    {
        "code": 200,
        "message": "更新成功",
        "data": {
            "id": 1,
            "name": "李四",
            ...
        }
    }
    ```
    
    Args:
        teacher_id: 教师 ID
        teacher_update: 更新数据
        db: 数据库会话
    
    Returns:
        dict: 更新成功响应
    
    Raises:
        HTTPException: 404 - 教师不存在
    """
    # 更新教师
    updated_teacher = crud.update_teacher(db, teacher_id, teacher_update)
    
    # 如果不存在，返回 404 错误
    if not updated_teacher:
        raise HTTPException(
            status_code=404,
            detail=f"教师不存在 (ID: {teacher_id})"
        )
    
    # 返回成功响应
    return create_response(
        data=TeacherResponse.model_validate(updated_teacher).model_dump(),
        message="更新成功"
    )


# -----------------------------------------
# 删除教师
# -----------------------------------------
@router.delete("/{teacher_id}", response_model=SimpleResponse)
async def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db)
):
    """
    删除教师
    
    执行软删除，数据不会真正从数据库中移除。
    
    **路径参数**:
    - teacher_id: 教师 ID
    
    **响应示例**:
    ```json
    {
        "code": 200,
        "message": "删除成功",
        "data": null
    }
    ```
    
    Args:
        teacher_id: 教师 ID
        db: 数据库会话
    
    Returns:
        SimpleResponse: 删除成功响应
    
    Raises:
        HTTPException: 404 - 教师不存在
    """
    # 删除教师
    success = crud.delete_teacher(db, teacher_id)
    
    # 如果不存在，返回 404 错误
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"教师不存在 (ID: {teacher_id})"
        )
    
    # 返回成功响应
    return SimpleResponse(
        code=200,
        message="删除成功",
        data=None
    )
