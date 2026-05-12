"""
========================================
数据库连接模块
========================================

这个模块负责：
1. 创建数据库引擎（与数据库建立连接）
2. 创建会话工厂（用于创建数据库操作会话）
3. 定义模型基类（所有数据库表模型的父类）

SQLAlchemy 简介：
- SQLAlchemy 是 Python 最流行的 ORM（对象关系映射）库
- ORM 的作用：用 Python 对象来操作数据库，不需要写 SQL 语句
- 比如：user = User(name="张三") 就能创建一条数据库记录

关键概念：
- Engine（引擎）：管理数据库连接池
- Session（会话）：执行数据库操作的上下文
- Base（基类）：所有数据库模型都要继承它

使用方法：
  from app.core.database import get_db, Base, engine
  
  # 创建表
  Base.metadata.create_all(bind=engine)
  
  # 获取数据库会话
  db = next(get_db())
"""

# -----------------------------------------
# 导入必要的模块
# -----------------------------------------
# create_engine: 创建数据库引擎
from sqlalchemy import create_engine

# sessionmaker: 创建会话工厂
# Session: 会话类型提示
from sqlalchemy.orm import sessionmaker, Session

# declarative_base: 创建模型基类
from sqlalchemy.orm import declarative_base

# 导入配置
from app.core.config import settings


# -----------------------------------------
# 创建数据库引擎
# -----------------------------------------
# 引擎是连接数据库的入口点
# 它管理一个连接池，可以高效地复用数据库连接

_engine_kwargs = {
    "echo": settings.DEBUG,
}

# SQLite 不支持 pool_pre_ping 和连接池高级特性
if settings.is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    settings.DATABASE_URL,
    **_engine_kwargs,
)


# -----------------------------------------
# 创建会话工厂
# -----------------------------------------
# SessionLocal 是一个"工厂"，每次调用 SessionLocal() 都会创建一个新的会话
# 会话用于执行数据库操作（查询、插入、更新、删除）

SessionLocal = sessionmaker(
    # 绑定到我们创建的引擎
    bind=engine,
    
    # autocommit=False: 不自动提交事务
    # 这样我们可以在一个事务中执行多个操作，然后一起提交
    autocommit=False,
    
    # autoflush=False: 不自动刷新
    # 刷新是指将内存中的更改同步到数据库
    autoflush=False,
)


# -----------------------------------------
# 创建模型基类
# -----------------------------------------
# Base 是所有数据库模型的父类
# 继承 Base 的类会被 SQLAlchemy 识别为数据库表模型

Base = declarative_base()


# -----------------------------------------
# 数据库会话依赖
# -----------------------------------------
def get_db():
    """
    获取数据库会话的生成器函数
    
    这个函数用于 FastAPI 的依赖注入系统。
    每次 API 请求都会创建一个新的数据库会话，
    请求结束后会话会被自动关闭。
    
    使用方法（在路由函数中）:
        @router.get("/")
        def get_items(db: Session = Depends(get_db)):
            # 使用 db 进行数据库操作
            items = db.query(Item).all()
            return items
    
    Yields:
        Session: 数据库会话对象
    
    工作流程:
        1. 创建新的数据库会话
        2. yield 返回会话给调用者使用
        3. 调用者使用完毕后，执行 finally 块关闭会话
    """
    # 创建一个新的数据库会话
    db = SessionLocal()
    
    try:
        # yield 将会话"借"给调用者使用
        # 调用者可以用这个会话进行数据库操作
        yield db
    finally:
        # 无论发生什么，最后都要关闭会话
        # 这样可以释放数据库连接，归还到连接池
        db.close()


# -----------------------------------------
# 测试代码
# -----------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("数据库连接测试")
    print("=" * 50)
    
    try:
        # 测试数据库连接
        # 使用 engine.connect() 尝试建立连接
        with engine.connect() as connection:
            print("✅ 数据库连接成功！")
            print(f"   连接 URL: {settings.DATABASE_URL}")
    except Exception as e:
        print("❌ 数据库连接失败！")
        print(f"   错误信息: {e}")
        print("")
        print("请检查：")
        print("1. PostgreSQL 是否已安装并启动")
        print("2. .env 文件中的数据库配置是否正确")
        print("3. 数据库 'schedule_db' 是否已创建")
    
    print("=" * 50)
