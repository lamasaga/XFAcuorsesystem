"""
========================================
依赖注入模块
========================================

这个模块定义了 FastAPI 的依赖项（Dependencies）。

什么是依赖注入？
- 依赖注入是一种设计模式，用于将"依赖"传递给需要它的函数
- 在 FastAPI 中，常用于：
  1. 获取数据库连接
  2. 验证用户权限
  3. 获取当前用户信息
  4. 参数验证和转换

为什么使用依赖注入？
1. 代码复用：同一个依赖可以在多个路由中使用
2. 解耦合：路由函数不需要知道如何创建依赖
3. 便于测试：可以轻松替换依赖进行测试
4. 自动文档：依赖的参数会自动出现在 API 文档中

使用方法：
  from fastapi import Depends
  from app.core.dependencies import get_db
  
  @router.get("/")
  def get_items(db: Session = Depends(get_db)):
      # db 是通过依赖注入获得的数据库会话
      return db.query(Item).all()
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# Generator: 类型提示，表示生成器函数
from typing import Generator

# Session: SQLAlchemy 会话类型
from sqlalchemy.orm import Session

# 导入数据库会话获取函数
from app.core.database import SessionLocal


# -----------------------------------------
# 数据库会话依赖
# -----------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖函数
    
    这是最常用的依赖，几乎每个需要访问数据库的 API 都会用到。
    
    工作原理：
    1. 当 API 被调用时，FastAPI 会先执行这个函数
    2. 函数创建一个数据库会话
    3. yield 将会话传递给 API 函数使用
    4. API 函数执行完毕后，finally 块关闭会话
    
    为什么用 yield 而不是 return？
    - yield 让函数变成"生成器"
    - 生成器可以在 yield 后暂停，等待调用者使用完毕
    - 使用完毕后继续执行 finally 块
    - 这样可以确保无论发生什么，数据库连接都会被正确关闭
    
    Returns:
        Generator[Session, None, None]: 数据库会话生成器
    
    Example:
        @router.get("/teachers")
        def get_teachers(db: Session = Depends(get_db)):
            # db 就是这个函数 yield 出来的会话
            teachers = db.query(Teacher).all()
            return teachers
    """
    # 创建新的数据库会话
    db = SessionLocal()
    
    try:
        # 将会话传递给调用者
        yield db
    finally:
        # 确保会话被关闭，释放数据库连接
        db.close()


# -----------------------------------------
# 分页参数依赖
# -----------------------------------------
class PaginationParams:
    """
    分页参数类
    
    用于处理列表 API 的分页请求。
    
    Attributes:
        page: 页码，从 1 开始
        page_size: 每页数量，默认 20
        skip: 跳过的记录数（内部计算）
    
    Example:
        @router.get("/teachers")
        def get_teachers(
            pagination: PaginationParams = Depends(),
            db: Session = Depends(get_db)
        ):
            teachers = db.query(Teacher).offset(pagination.skip).limit(pagination.page_size).all()
            return teachers
    """
    
    def __init__(
        self,
        page: int = 1,      # 页码，默认第 1 页
        page_size: int = 20  # 每页数量，默认 20 条
    ):
        """
        初始化分页参数
        
        Args:
            page: 页码，必须大于 0
            page_size: 每页数量，范围 1-100
        """
        # 确保页码至少为 1
        self.page = max(1, page)
        
        # 确保每页数量在合理范围内
        self.page_size = min(max(1, page_size), 100)
        
        # 计算需要跳过的记录数
        # 例如：第 2 页，每页 20 条，则跳过 (2-1)*20=20 条
        self.skip = (self.page - 1) * self.page_size


# -----------------------------------------
# 通用响应格式
# -----------------------------------------
def create_response(
    data=None,
    message: str = "success",
    code: int = 200
) -> dict:
    """
    创建统一的 API 响应格式
    
    所有 API 返回的数据都应该使用统一的格式，
    这样前端处理起来更方便。
    
    Args:
        data: 响应数据，可以是任意类型
        message: 响应消息
        code: 状态码
    
    Returns:
        dict: 统一格式的响应字典
    
    Example:
        return create_response(
            data={"id": 1, "name": "张三"},
            message="获取成功"
        )
        
        # 返回:
        # {
        #     "code": 200,
        #     "message": "获取成功",
        #     "data": {"id": 1, "name": "张三"}
        # }
    """
    return {
        "code": code,
        "message": message,
        "data": data
    }


def create_pagination_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "success"
) -> dict:
    """
    创建分页列表的响应格式
    
    用于返回带分页信息的列表数据。
    
    Args:
        items: 数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量
        message: 响应消息
    
    Returns:
        dict: 带分页信息的响应字典
    
    Example:
        teachers = db.query(Teacher).all()
        return create_pagination_response(
            items=teachers,
            total=100,
            page=1,
            page_size=20
        )
    """
    return {
        "code": 200,
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size  # 总页数
        }
    }
