"""
========================================
排课系统后端 - 应用入口文件
========================================

这是整个后端应用的"大门"，负责：
1. 创建 FastAPI 应用实例
2. 注册所有的 API 路由（接口）
3. 配置跨域访问（让前端能够调用后端 API）
4. 启动时初始化数据库

运行方法：
  在 backend 目录下运行: uvicorn app.main:app --reload

  --reload 表示代码修改后自动重启服务器（开发时使用）

访问地址：
  - API 文档: http://localhost:8000/docs
  - 备用文档: http://localhost:8000/redoc
  - 根路径:   http://localhost:8000/
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# FastAPI: Web 框架核心
from fastapi import FastAPI

# CORSMiddleware: 处理跨域请求
# 跨域问题：浏览器出于安全考虑，默认不允许网页访问不同域名的接口
# 比如前端在 localhost:3000，后端在 localhost:8000，就是跨域
from fastapi.middleware.cors import CORSMiddleware

# 导入数据库引擎和 Base（用于创建表）
from app.core.database import engine, Base

# 导入配置
from app.core.config import settings

# -----------------------------------------
# 导入各个模块的路由
# -----------------------------------------
# 路由(Router)：定义了 API 的路径和处理函数
from app.modules.teachers.router import router as teachers_router
from app.modules.classes.router import router as classes_router
from app.modules.subjects.router import router as subjects_router
from app.modules.tasks.router import router as tasks_router
from app.modules.layers.router import router as layers_router
from app.modules.venues.router import router as venues_router
from app.modules.schedules.router import router as schedules_router
from app.modules.stats.router import router as stats_router
from app.modules.students.router import router as students_router
from app.modules.alevel_subjects.router import router as alevel_subjects_router
from app.modules.course_selections.router import router as course_selections_router
from app.modules.course_classes.router import router as course_classes_router
from app.modules.time_slots.router import router as time_slots_router

# 导入 time_slots 模型（确保 Base.metadata 包含该表）
from app.modules.time_slots.models import TimeSlotConfig


# -----------------------------------------
# 创建 FastAPI 应用实例
# -----------------------------------------
app = FastAPI(
    # 应用标题（显示在 API 文档中）
    title=settings.APP_NAME,
    
    # 应用描述
    description="""
    ## 学校智能排课系统 API
    
    提供以下功能：
    - 📚 教师管理：添加、修改、删除、查询教师信息
    - 🏫 班级管理：管理班级信息
    - 📖 科目管理：管理科目信息
    - 📋 教学任务：管理教师-班级-科目的任务分配
    """,
    
    # API 版本
    version="1.0.0",
    
    # API 文档路径
    docs_url="/docs",
    redoc_url="/redoc",
)


# -----------------------------------------
# 配置跨域访问（CORS）
# -----------------------------------------
# 允许前端应用访问后端 API
app.add_middleware(
    CORSMiddleware,
    # 允许的来源（前端地址）
    # ["*"] 表示允许所有来源，生产环境应该限制为具体的前端地址
    allow_origins=["*"],
    
    # 允许携带凭证（如 Cookie）
    allow_credentials=True,
    
    # 允许的 HTTP 方法
    allow_methods=["*"],
    
    # 允许的请求头
    allow_headers=["*"],
)


# -----------------------------------------
# 注册路由
# -----------------------------------------
# 将各个模块的路由注册到主应用
# prefix: API 路径前缀，比如 /api/v1/teachers
# tags: 在 API 文档中的分组标签

app.include_router(
    teachers_router,
    prefix=f"{settings.API_PREFIX}/teachers",
    tags=["教师管理"]
)

app.include_router(
    classes_router,
    prefix=f"{settings.API_PREFIX}/classes",
    tags=["班级管理"]
)

app.include_router(
    subjects_router,
    prefix=f"{settings.API_PREFIX}/subjects",
    tags=["科目管理"]
)

app.include_router(
    tasks_router,
    prefix=f"{settings.API_PREFIX}/tasks",
    tags=["教学任务"]
)

app.include_router(
    layers_router,
    prefix=f"{settings.API_PREFIX}/layers",
    tags=["分层课程"]
)

app.include_router(
    venues_router,
    prefix=f"{settings.API_PREFIX}/venues",
    tags=["场地资源"]
)

app.include_router(
    schedules_router,
    prefix=f"{settings.API_PREFIX}/schedules",
    tags=["排课管理"]
)

app.include_router(
    stats_router,
    prefix=f"{settings.API_PREFIX}/stats",
    tags=["统计数据"]
)

app.include_router(
    students_router,
    prefix=f"{settings.API_PREFIX}/students",
    tags=["学生管理"]
)

app.include_router(
    alevel_subjects_router,
    prefix=f"{settings.API_PREFIX}/alevel-subjects",
    tags=["A-Level科目"]
)

app.include_router(
    course_selections_router,
    prefix=f"{settings.API_PREFIX}/course-selections",
    tags=["选课管理"]
)

app.include_router(
    course_classes_router,
    prefix=f"{settings.API_PREFIX}/course-classes",
    tags=["课程班管理"]
)
app.include_router(
    time_slots_router,
    prefix=f"{settings.API_PREFIX}/time-slots",
    tags=["时间槽配置"]
)



# -----------------------------------------
# 启动事件
# -----------------------------------------
@app.on_event("startup")
async def startup():
    """
    应用启动时执行的函数
    
    主要作用：
    1. 创建数据库表（如果不存在）
    2. 输出启动信息
    """
    print("=" * 50)
    print(f"[启动] {settings.APP_NAME} 正在启动...")
    print("=" * 50)
    
    # 创建数据库表（如果不存在）
    Base.metadata.create_all(bind=engine)
    
    # 初始化时间槽配置数据（如果表为空）
    from app.core.database import SessionLocal
    from app.modules.time_slots.init_data import init_time_slot_configs
    db = SessionLocal()
    try:
        init_time_slot_configs(db)
    finally:
        db.close()
    
    # 打印所有路由
    print("[路由] 已注册的 API 路由:")
    for route in app.routes:
        if hasattr(route, "methods"):
            methods = ",".join(route.methods)
            print(f"   {methods} {route.path}")
            
    print("[完成] 数据库表创建/检查完成")
    print(f"[文档] API 文档地址: http://localhost:8000/docs")
    print("=" * 50)


# -----------------------------------------
# 根路径接口
# -----------------------------------------
@app.get("/")
async def root():
    """
    根路径接口
    
    用于检查服务是否正常运行
    
    Returns:
        dict: 包含欢迎信息和 API 文档链接
    """
    return {
        "message": "欢迎使用排课系统 API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """
    健康检查接口
    
    用于监控系统检查服务是否正常
    
    Returns:
        dict: 服务状态信息
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


# -----------------------------------------
# 开发模式下直接运行
# -----------------------------------------
# 这段代码只在直接运行 main.py 时执行
# 正式部署时应该使用 uvicorn 命令启动
if __name__ == "__main__":
    import uvicorn
    
    # 启动服务器
    # host="0.0.0.0" 表示允许外部访问
    # port=8000 是端口号
    # reload=True 表示代码修改后自动重启
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
