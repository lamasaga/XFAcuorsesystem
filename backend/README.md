# 排课系统后端

> 基于 FastAPI + PostgreSQL 的后端服务

　　对应 GitHub 仓库目录名：**[XFAcuorsesystem](https://github.com/lamasaga/XFAcuorsesystem)**（克隆后 `cd XFAcuorsesystem/backend` 进入本目录）。

---

## 环境要求

- Python 3.10+
- PostgreSQL 16+

---

## 快速开始

### 第一步：安装 PostgreSQL

1. 下载 PostgreSQL
   - 访问 https://www.postgresql.org/download/windows/
   - 下载 PostgreSQL 16 Windows 安装包

2. 安装时注意事项
   - 记住设置的密码（建议用简单的如 `123456`）
   - 默认端口是 `5432`，不要修改
   - 勾选安装 pgAdmin（数据库管理工具）

3. 创建数据库
   - 打开 pgAdmin
   - 右键 `Databases` → `Create` → `Database`
   - 输入名称：`schedule_db`
   - 点击 Save

### 第二步：安装 Python 依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（可选但推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如果安装速度慢，使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 第三步：配置环境变量

编辑 `.env` 文件，修改数据库密码：

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=你的密码  # 改成你安装 PostgreSQL 时设置的密码
DB_NAME=schedule_db
```

### 第四步：启动服务

```bash
# 在 backend 目录下运行
uvicorn app.main:app --reload
```

看到以下输出说明启动成功：

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
🚀 排课系统后端 正在启动...
✅ 数据库表创建/检查完成
```

### 第五步：访问 API 文档

打开浏览器访问：http://localhost:8000/docs

你会看到自动生成的 API 文档，可以直接在网页上测试 API。

---

## 项目结构

```
backend/
├── app/
│   ├── __init__.py          # 包初始化
│   ├── main.py              # 应用入口 ⭐
│   │
│   ├── core/                # 核心配置
│   │   ├── config.py        # 配置管理（读取 .env）
│   │   ├── database.py      # 数据库连接
│   │   └── dependencies.py  # 依赖注入
│   │
│   └── modules/             # 业务模块
│       ├── teachers/        # 教师管理
│       │   ├── models.py    # 数据库模型（表结构）
│       │   ├── schemas.py   # 数据验证（请求/响应格式）
│       │   ├── crud.py      # 数据库操作
│       │   └── router.py    # API 路由
│       │
│       ├── classes/         # 班级管理
│       ├── subjects/        # 科目管理
│       └── tasks/           # 教学任务
│
├── requirements.txt         # Python 依赖
├── .env                     # 环境变量配置
└── README.md               # 本文件
```

---

## API 接口列表

### 教师管理 `/api/v1/teachers`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/teachers` | 获取教师列表 |
| GET | `/teachers/{id}` | 获取单个教师 |
| POST | `/teachers` | 创建教师 |
| PUT | `/teachers/{id}` | 更新教师 |
| DELETE | `/teachers/{id}` | 删除教师 |

### 班级管理 `/api/v1/classes`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/classes` | 获取班级列表 |
| GET | `/classes/{id}` | 获取单个班级 |
| POST | `/classes` | 创建班级 |
| PUT | `/classes/{id}` | 更新班级 |
| DELETE | `/classes/{id}` | 删除班级 |

### 科目管理 `/api/v1/subjects`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/subjects` | 获取科目列表 |
| GET | `/subjects/{id}` | 获取单个科目 |
| POST | `/subjects` | 创建科目 |
| PUT | `/subjects/{id}` | 更新科目 |
| DELETE | `/subjects/{id}` | 删除科目 |

### 教学任务 `/api/v1/tasks`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/tasks` | 获取任务列表 |
| GET | `/tasks/with-details` | 获取包含详情的任务列表 |
| POST | `/tasks` | 创建任务 |
| POST | `/tasks/batch` | 批量创建任务 |
| PUT | `/tasks/{id}` | 更新任务 |
| DELETE | `/tasks/{id}` | 删除任务 |

---

## 常见问题

### 1. 数据库连接失败

**错误信息**：`connection refused` 或 `could not connect to server`

**解决方法**：
1. 检查 PostgreSQL 服务是否启动
2. 检查 `.env` 文件中的密码是否正确
3. 检查数据库 `schedule_db` 是否已创建

### 2. 端口被占用

**错误信息**：`Address already in use`

**解决方法**：
```bash
# 使用其他端口启动
uvicorn app.main:app --reload --port 8001
```

### 3. 导入模块失败

**错误信息**：`ModuleNotFoundError`

**解决方法**：
1. 确保在 `backend` 目录下运行命令
2. 确保已激活虚拟环境
3. 确保已安装所有依赖

---

## 开发指南

### 添加新的业务模块

1. 在 `app/modules/` 下创建新目录
2. 创建以下文件：
   - `__init__.py` - 包初始化
   - `models.py` - 数据库模型
   - `schemas.py` - 数据验证
   - `crud.py` - 数据库操作
   - `router.py` - API 路由

3. 在 `app/main.py` 中注册路由：
   ```python
   from app.modules.xxx.router import router as xxx_router
   app.include_router(xxx_router, prefix="/api/v1/xxx", tags=["XXX管理"])
   ```

### 数据库迁移（后续扩展）

如果需要修改表结构，建议使用 Alembic 进行数据库迁移：

```bash
# 安装 alembic
pip install alembic

# 初始化
alembic init alembic

# 创建迁移脚本
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

---

## 技术栈说明

| 技术 | 作用 | 文档 |
|------|------|------|
| FastAPI | Web 框架 | https://fastapi.tiangolo.com/zh/ |
| SQLAlchemy | ORM 数据库操作 | https://www.sqlalchemy.org/ |
| Pydantic | 数据验证 | https://docs.pydantic.dev/ |
| PostgreSQL | 关系型数据库 | https://www.postgresql.org/ |
| Uvicorn | ASGI 服务器 | https://www.uvicorn.org/ |
