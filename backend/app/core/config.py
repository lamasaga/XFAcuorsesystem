"""
========================================
应用配置模块
========================================

这个模块负责管理应用的所有配置项。
配置值从环境变量（.env 文件）中读取。

支持两种数据库模式：
1. PostgreSQL（默认）: 需要安装 PostgreSQL
2. SQLite（桌面模式）: 设置 USE_SQLITE=true，无需安装数据库

使用方法：
  from app.core.config import settings
  
  # 读取配置
  db_host = settings.DB_HOST
  app_name = settings.APP_NAME
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    应用配置类
    
    继承自 BaseSettings，自动从环境变量读取配置。
    变量名必须与 .env 文件中的键名一致（不区分大小写）。
    """
    
    # -----------------------------------------
    # 应用基础配置
    # -----------------------------------------
    APP_NAME: str = "排课系统后端"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    
    # -----------------------------------------
    # 数据库模式选择
    # -----------------------------------------
    # 设为 true 则使用 SQLite（桌面/便携模式），无需安装 PostgreSQL
    USE_SQLITE: bool = False
    
    # SQLite 数据库文件路径（USE_SQLITE=true 时生效）
    # 默认存放在 backend/data/schedule.db
    SQLITE_PATH: str = ""
    
    # -----------------------------------------
    # PostgreSQL 数据库配置（USE_SQLITE=false 时生效）
    # -----------------------------------------
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "schedule_db"
    
    # -----------------------------------------
    # 计算属性
    # -----------------------------------------
    @property
    def DATABASE_URL(self) -> str:
        """
        生成数据库连接 URL
        
        根据 USE_SQLITE 环境变量自动选择数据库：
        - SQLite: sqlite:///path/to/schedule.db
        - PostgreSQL: postgresql://user:pass@host:port/db
        """
        if self.USE_SQLITE or os.getenv("USE_SQLITE", "false").lower() == "true":
            db_path = self.SQLITE_PATH
            if not db_path:
                # 默认路径: backend/data/schedule.db
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)
                )))
                data_dir = os.path.join(base_dir, "data")
                os.makedirs(data_dir, exist_ok=True)
                db_path = os.path.join(data_dir, "schedule.db")
            return f"sqlite:///{db_path}"
        
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def is_sqlite(self) -> bool:
        """判断当前是否使用 SQLite"""
        return self.USE_SQLITE or os.getenv("USE_SQLITE", "false").lower() == "true"
    
    # -----------------------------------------
    # Pydantic 配置
    # -----------------------------------------
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# -----------------------------------------
# 创建全局配置实例
# -----------------------------------------
# 这是一个单例模式的配置对象
# 整个应用都使用这同一个 settings 实例
settings = Settings()


# -----------------------------------------
# 测试代码
# -----------------------------------------
# 直接运行这个文件可以测试配置是否正确读取
if __name__ == "__main__":
    print("=" * 50)
    print("配置测试")
    print("=" * 50)
    print(f"应用名称: {settings.APP_NAME}")
    print(f"调试模式: {settings.DEBUG}")
    print(f"API 前缀: {settings.API_PREFIX}")
    print(f"数据库主机: {settings.DB_HOST}")
    print(f"数据库端口: {settings.DB_PORT}")
    print(f"数据库用户: {settings.DB_USER}")
    print(f"数据库名称: {settings.DB_NAME}")
    print(f"数据库 URL: {settings.DATABASE_URL}")
    print("=" * 50)
