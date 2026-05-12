"""
========================================
教师数据验证模式（Schemas）
========================================

这个文件定义了教师数据的验证规则和格式。

Pydantic 模式的作用：
1. 数据验证：自动检查请求数据是否符合要求
2. 数据转换：自动将 JSON 转换为 Python 对象
3. API 文档：自动生成请求/响应的数据格式说明
4. IDE 支持：提供代码补全和类型检查

Schema vs Model 的区别：
- Model（models.py）：定义数据库表结构，用于数据持久化
- Schema（schemas.py）：定义 API 数据格式，用于请求/响应验证

常用的 Schema 类型：
- XxxBase：基础字段，被其他 Schema 继承
- XxxCreate：创建时需要的字段
- XxxUpdate：更新时需要的字段
- XxxResponse：响应时返回的字段
- XxxInDB：数据库中的完整字段

使用方法：
    # 在路由中使用
    @router.post("/", response_model=TeacherResponse)
    def create_teacher(teacher: TeacherCreate):
        # teacher 已经被验证过了，可以直接使用
        pass
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# BaseModel: Pydantic 模型基类
from pydantic import BaseModel, Field

# Optional: 表示字段可以为 None
# List: 列表类型
from typing import Optional, List

# datetime: 日期时间类型
from datetime import datetime


# -----------------------------------------
# 基础模式
# -----------------------------------------
class TeacherBase(BaseModel):
    """
    教师基础模式
    
    包含教师的基本字段，被其他模式继承。
    使用 Field() 可以添加字段描述和验证规则。
    
    Attributes:
        name: 教师姓名
        type: 教师类型
        department: 所属学部
        subjects: 任教科目
        tags: 教师标签
        max_weekly_hours: 每周最大课时
        unavailable_slots: 不可用时间槽
    """
    
    # name: 教师姓名
    # min_length=1: 至少 1 个字符
    # max_length=50: 最多 50 个字符
    name: str = Field(
        ...,  # ... 表示必填字段
        min_length=1,
        max_length=50,
        description="教师姓名",
        examples=["张三"]
    )
    
    # type: 教师类型
    # 只能是 "CN" 或 "EN"
    type: str = Field(
        default="CN",
        description="教师类型：CN=中教，EN=外教",
        examples=["CN"]
    )
    
    # department: 所属学部
    department: str = Field(
        default="PRIMARY",
        description="所属学部：PRIMARY=小学部，SECONDARY=中学部，BOTH=小中贯通",
        examples=["PRIMARY"]
    )
    
    # subjects: 任教科目列表
    subjects: List[str] = Field(
        default=[],
        description="任教科目列表",
        examples=[["语文", "数学"]]
    )
    
    # tags: 教师标签列表
    tags: List[str] = Field(
        default=[],
        description="教师标签，如 HOMEROOM_TEACHER",
        examples=[["HOMEROOM_TEACHER"]]
    )
    
    # max_weekly_hours: 每周最大课时数
    max_weekly_hours: int = Field(
        default=25,
        ge=1,  # >= 1
        le=40,  # <= 40
        description="每周最大课时数",
        examples=[25]
    )
    
    # unavailable_slots: 不可用时间槽（可选）
    unavailable_slots: Optional[dict] = Field(
        default={},
        description="不可用时间槽，格式：{'1': [1,2], '3': [5,6]}",
        examples=[{"1": [1, 2]}]
    )
    
    # daily_shifts: 每日班次状态
    daily_shifts: Optional[dict] = Field(
        default={"1": "morning", "2": "morning", "3": "morning", "4": "morning", "5": "morning"},
        description="每日班次状态，格式：{'1': 'morning', '2': 'evening', ...}，morning=早班，evening=晚班",
        examples=[{"1": "morning", "2": "morning", "3": "evening", "4": "evening", "5": "morning"}]
    )

    # research_group_id: 所属教研组
    research_group_id: Optional[int] = Field(
        default=None,
        description="所属教研组ID"
    )


# -----------------------------------------
# 创建模式
# -----------------------------------------
class TeacherCreate(TeacherBase):
    """
    创建教师时使用的模式
    
    继承自 TeacherBase，包含创建教师所需的所有字段。
    前端发送 POST 请求创建教师时，请求体需要符合这个格式。
    
    Example:
        POST /api/v1/teachers
        {
            "name": "张三",
            "type": "CN",
            "department": "PRIMARY",
            "subjects": ["语文", "数学"],
            "tags": ["HOMEROOM_TEACHER"],
            "max_weekly_hours": 25
        }
    """
    pass  # 使用 TeacherBase 的所有字段


# -----------------------------------------
# 更新模式
# -----------------------------------------
class TeacherUpdate(BaseModel):
    """
    更新教师时使用的模式
    
    所有字段都是可选的（Optional），
    只更新提供的字段，未提供的字段保持原值。
    
    Example:
        PUT /api/v1/teachers/1
        {
            "name": "李四"  # 只更新姓名
        }
    """
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="教师姓名"
    )
    
    type: Optional[str] = Field(
        None,
        description="教师类型"
    )
    
    department: Optional[str] = Field(
        None,
        description="所属学部"
    )
    
    subjects: Optional[List[str]] = Field(
        None,
        description="任教科目列表"
    )
    
    tags: Optional[List[str]] = Field(
        None,
        description="教师标签"
    )
    
    max_weekly_hours: Optional[int] = Field(
        None,
        ge=1,
        le=40,
        description="每周最大课时数"
    )
    
    unavailable_slots: Optional[dict] = Field(
        None,
        description="不可用时间槽"
    )
    
    daily_shifts: Optional[dict] = Field(
        None,
        description="每日班次状态"
    )

    research_group_id: Optional[int] = Field(
        None,
        description="所属教研组ID"
    )


# -----------------------------------------
# 教研组模式
# -----------------------------------------
class ResearchGroupCreate(BaseModel):
    """创建教研组"""
    name: str = Field(..., min_length=1, max_length=50, description="教研组名称")

class ResearchGroupResponse(BaseModel):
    """教研组响应"""
    id: int
    name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ResearchGroupListResponse(BaseModel):
    """教研组列表响应"""
    code: int = 200
    message: str = "success"
    data: dict


# -----------------------------------------
# 响应模式
# -----------------------------------------
class TeacherResponse(TeacherBase):
    """
    教师响应模式
    
    API 返回教师数据时使用的格式。
    包含数据库中的完整字段，如 id、创建时间等。
    
    配置说明：
    - from_attributes=True（原 orm_mode=True）:
      允许直接从 SQLAlchemy 模型对象转换为 Pydantic 模型
    
    Example:
        # 路由返回
        @router.get("/{id}", response_model=TeacherResponse)
        
        # 响应数据
        {
            "id": 1,
            "name": "张三",
            "type": "CN",
            "department": "PRIMARY",
            "subjects": ["语文"],
            "tags": ["HOMEROOM_TEACHER"],
            "max_weekly_hours": 25,
            "weekly_hours": 18,
            "created_at": "2024-01-01T00:00:00"
        }
    """
    
    # 数据库生成的字段
    id: int = Field(..., description="教师ID")
    weekly_hours: int = Field(default=0, description="当前周课时数")
    research_group_id: Optional[int] = Field(None, description="所属教研组ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # Pydantic 配置
    class Config:
        """Pydantic 配置"""
        # 允许从 ORM 模型转换
        from_attributes = True


# -----------------------------------------
# 列表响应模式
# -----------------------------------------
class TeacherListResponse(BaseModel):
    """
    教师列表响应模式
    
    返回教师列表时使用的格式，包含分页信息。
    
    Example:
        {
            "code": 200,
            "message": "success",
            "data": {
                "items": [...],
                "total": 100,
                "page": 1,
                "page_size": 20
            }
        }
    """
    
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: dict = Field(..., description="数据")


# -----------------------------------------
# 简单响应模式
# -----------------------------------------
class SimpleResponse(BaseModel):
    """
    简单响应模式
    
    用于删除等操作的响应。
    
    Example:
        {
            "code": 200,
            "message": "删除成功",
            "data": null
        }
    """
    
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="消息")
    data: Optional[dict] = Field(None, description="数据")
