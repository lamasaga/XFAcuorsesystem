"""
桌面模式启动脚本

用于 Electron 桌面应用调用，特点：
1. 使用 SQLite 数据库（无需安装 PostgreSQL）
2. 自动创建数据库表
3. 绑定 127.0.0.1 限制本地访问
"""

import os
import sys

# 设置环境变量：启用 SQLite 模式
os.environ["USE_SQLITE"] = "true"
os.environ["DEBUG"] = "false"

# 确保能找到 app 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """启动桌面模式后端服务"""
    print("=" * 50)
    print("  智能排课系统 - 桌面模式启动")
    print("  数据库: SQLite (免安装)")
    print("=" * 50)

    # 导入并创建数据库表
    from app.core.database import engine, Base
    from app.core.config import settings

    print(f"  数据库路径: {settings.DATABASE_URL}")

    # 导入所有模型以注册到 Base
    from app.modules.teachers.models import Teacher, ResearchGroup
    from app.modules.classes.models import Class
    from app.modules.subjects.models import Subject
    from app.modules.tasks.models import TeachingTask
    from app.modules.layers.models import LayerGroup
    from app.modules.venues.models import Venue
    from app.modules.schedules.models import Schedule, ScheduleItem, ScheduleConfig

    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("  数据库表已就绪")
    print("=" * 50)

    # 导入 FastAPI 应用实例（直接传对象，避免 PyInstaller 下字符串导入失败）
    from app.main import app as application

    # 启动 uvicorn（传入 app 对象而非字符串，兼容 PyInstaller 打包）
    import uvicorn
    uvicorn.run(
        application,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
