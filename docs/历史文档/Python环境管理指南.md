# Python 环境管理指南

> 本文档总结了排课系统开发过程中遇到的环境问题，并系统性地讲解 Python 环境管理知识，帮助新手理解和解决类似问题。

---

## 目录

1. [我们遇到了什么问题？](#我们遇到了什么问题)
2. [问题的根本原因](#问题的根本原因)
3. [什么是虚拟环境？](#什么是虚拟环境)
4. [Python 环境管理基础](#python-环境管理基础)
5. [常见问题排查思路](#常见问题排查思路)
6. [最佳实践总结](#最佳实践总结)

---

## 我们遇到了什么问题？

### 问题时间线回顾

我们在调试过程中遇到了一连串的问题，这里按顺序梳理：

```
问题1: 404 Not Found (API路由找不到)
    ↓ 修复后
问题2: 500 Internal Server Error (服务器内部错误)
    ↓ 分析发现是数据库字段缺失
问题3: UndefinedColumn (数据库字段不存在)
    ↓ 需要重置数据库
问题4: reset_db.py 执行失败 (外键约束)
    ↓ 修复脚本后
问题5: No module named pip / uvicorn
    ↓ 虚拟环境损坏
问题6: 需要重建虚拟环境
    ↓ 最终成功
```

### 每个问题的具体情况

#### 问题1：404 Not Found

**现象**：前端调用 `POST /api/v1/schedules/generate` 时返回 404

**原因**：路由注册时出现了"双重前缀"问题

```python
# router.py 中定义了前缀
router = APIRouter(prefix="/schedules")

# main.py 中又加了前缀
app.include_router(router, prefix="/api/v1/schedules")

# 结果：实际路径变成了 /api/v1/schedules/schedules/generate
```

**解决**：在 `router.py` 中移除 `prefix`，让 `main.py` 统一管理前缀

#### 问题2 & 3：数据库字段不存在

**现象**：`psycopg2.errors.UndefinedColumn: 字段 teaching_tasks.layer_group_id 不存在`

**原因**：
- 我们在代码中给 `TeachingTask` 模型添加了新字段 `layer_group_id`
- 但数据库中的表还是旧的结构，没有这个字段
- **代码和数据库不同步**

**类比理解**：
> 就像你在 Excel 表格模板里加了一列，但实际存数据的那个文件还是旧版本，没有这一列

#### 问题4：重置脚本失败

**现象**：运行 `reset_db.py` 时报外键约束错误

**原因**：删除表的顺序不对。数据库中：
- `ScheduleItem` 依赖 `TeachingTask`（外键关联）
- 如果先删 `TeachingTask`，数据库会拒绝（因为还有表在引用它）

**解决**：调整删除顺序，先删子表，再删父表

#### 问题5 & 6：虚拟环境损坏

**现象**：
```
No module named pip
No module named uvicorn
```

**原因**：虚拟环境（`.venv` 文件夹）损坏或不完整

**解决**：删除旧的虚拟环境，重新创建

---

## 什么是虚拟环境？

### 通俗解释

**虚拟环境 (Virtual Environment)** 是 Python 的一个"隔离空间"。

想象一下这个场景：
- 项目 A 需要用 `requests` 库的 1.0 版本
- 项目 B 需要用 `requests` 库的 2.0 版本
- 如果都装在同一个地方，就会冲突！

虚拟环境就像是给每个项目一个**独立的工具箱**：

```
你的电脑
├── 系统 Python（全局）
│   └── 一些基础库
│
├── 项目A 的虚拟环境（.venv）
│   └── requests 1.0
│   └── flask 2.0
│   └── ...
│
└── 项目B 的虚拟环境（.venv）
    └── requests 2.0
    └── django 4.0
    └── ...
```

### 为什么需要虚拟环境？

| 不用虚拟环境 | 用虚拟环境 |
|-------------|-----------|
| 所有项目共享同一套库 | 每个项目有独立的库 |
| 版本容易冲突 | 版本隔离，互不影响 |
| 难以知道项目需要哪些库 | 项目依赖清晰可见 |
| 升级一个库可能破坏其他项目 | 升级只影响当前项目 |

### 虚拟环境的本质

虚拟环境实际上就是一个文件夹（通常叫 `.venv` 或 `venv`），里面包含：

```
.venv/
├── Scripts/          # Windows 下的可执行文件
│   ├── python.exe    # 这个虚拟环境专用的 Python
│   ├── pip.exe       # 这个虚拟环境专用的 pip
│   ├── activate      # 激活脚本
│   └── ...
├── Lib/
│   └── site-packages/  # 安装的第三方库都在这里
│       ├── fastapi/
│       ├── sqlalchemy/
│       └── ...
└── pyvenv.cfg        # 配置文件
```

当你"激活"虚拟环境时，系统会优先使用 `.venv/Scripts/` 里的 Python 和 pip。

---

## Python 环境管理基础

### 核心概念图解

```
┌─────────────────────────────────────────────────────────────┐
│                      你的电脑                                │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────────────────┐  │
│  │   系统 Python    │      │      项目文件夹              │  │
│  │                 │      │                             │  │
│  │  C:\Python310\  │      │  C:\排课系统\               │  │
│  │  ├── python.exe │      │  ├── backend\              │  │
│  │  └── pip.exe    │      │  │   ├── .venv\ ←虚拟环境  │  │
│  │                 │      │  │   ├── app\              │  │
│  │  这是"全局"的    │      │  │   └── requirements.txt  │  │
│  │  所有人共享      │      │  └── frontend\            │  │
│  └─────────────────┘      └─────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 关键命令速查

#### 1. 创建虚拟环境

```powershell
# 进入项目目录
cd C:\Users\MECHREVO\Desktop\排课系统\backend

# 创建虚拟环境（在当前目录下创建 .venv 文件夹）
python -m venv .venv
```

**解释**：
- `python -m venv` = 用 Python 运行 venv 模块
- `.venv` = 虚拟环境的文件夹名（可以自定义，但 .venv 是惯例）

#### 2. 激活虚拟环境

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate

# 激活成功后，命令行前面会出现 (.venv) 标记
# (.venv) PS C:\Users\MECHREVO\Desktop\排课系统\backend>
```

**如何判断是否激活？**
- 看命令行开头是否有 `(.venv)` 或类似标记
- 运行 `where python` 看路径是否指向 `.venv\Scripts\python.exe`

#### 3. 安装依赖

```powershell
# 确保已激活虚拟环境！
# 安装 requirements.txt 中列出的所有库
pip install -r requirements.txt

# 安装单个库
pip install fastapi
```

#### 4. 退出虚拟环境

```powershell
deactivate
```

#### 5. 删除虚拟环境

虚拟环境就是一个文件夹，直接删除即可：

```powershell
# 先退出虚拟环境
deactivate

# 删除文件夹
Remove-Item -Recurse -Force .venv
```

### pip 是什么？

**pip** 是 Python 的包管理器，类似于：
- 手机的应用商店
- Node.js 的 npm
- Java 的 Maven

它的作用是从 PyPI（Python Package Index，Python 官方的库仓库）下载和安装第三方库。

```powershell
# 常用 pip 命令
pip install 库名          # 安装库
pip uninstall 库名        # 卸载库
pip list                  # 列出已安装的库
pip freeze                # 列出已安装的库（带版本号）
pip show 库名             # 显示库的详细信息
```

### requirements.txt 的作用

这个文件记录了项目需要的所有依赖库：

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
```

- `==` 后面是精确的版本号
- 这样任何人拿到项目，运行 `pip install -r requirements.txt` 就能安装完全相同的环境

---

## 常见问题排查思路

### 问题排查流程图

```
遇到错误
    │
    ▼
┌───────────────────────────────────────────┐
│ 第一步：看错误信息                          │
│ - 什么类型的错误？                          │
│ - 404? 500? ModuleNotFound? 语法错误?      │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│ 第二步：确认环境状态                         │
│ - 虚拟环境激活了吗？(.venv)                 │
│ - 在正确的目录吗？                          │
│ - 后端服务在运行吗？                        │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│ 第三步：根据错误类型处理                     │
└───────────────────────────────────────────┘
```

### 常见错误及解决方案

#### 错误1：`ModuleNotFoundError: No module named 'xxx'`

**含义**：Python 找不到这个库

**排查步骤**：
1. 虚拟环境激活了吗？
   ```powershell
   .\.venv\Scripts\Activate
   ```
2. 库安装了吗？
   ```powershell
   pip list | findstr xxx
   ```
3. 如果没安装：
   ```powershell
   pip install -r requirements.txt
   ```

#### 错误2：`404 Not Found`

**含义**：请求的 API 路径不存在

**排查步骤**：
1. 后端服务在运行吗？
2. 查看后端打印的路由列表，确认路径是否正确
3. 检查前端请求的 URL 是否与后端注册的一致
4. 检查是否有"双重前缀"问题

#### 错误3：`500 Internal Server Error`

**含义**：服务器内部出错了

**排查步骤**：
1. 看后端终端的详细错误信息（通常会打印完整的报错）
2. 根据报错定位问题：
   - 数据库相关 → 检查数据库连接、表结构
   - 代码逻辑 → 检查相关代码

#### 错误4：数据库字段不存在 (`UndefinedColumn`)

**含义**：代码里用了某个字段，但数据库表里没有

**原因**：修改了 models.py 但没有更新数据库

**解决**：
```powershell
# 运行重置脚本（开发阶段）
python reset_db.py
python init_data.py
```

#### 错误5：虚拟环境损坏

**现象**：`No module named pip` 或激活后各种命令都不工作

**解决**：重建虚拟环境
```powershell
# 1. 退出并删除旧环境
deactivate
Remove-Item -Recurse -Force .venv

# 2. 创建新环境
python -m venv .venv

# 3. 激活
.\.venv\Scripts\Activate

# 4. 安装依赖
pip install -r requirements.txt
```

---

## 最佳实践总结

### 日常开发工作流

```
每次开始工作时：
1. 打开终端
2. cd 到项目目录
3. 激活虚拟环境
4. 启动后端服务
5. 另开终端启动前端

每次结束工作时：
1. Ctrl+C 停止服务
2. deactivate 退出虚拟环境（可选）
```

### 具体命令

```powershell
# === 启动后端 ===
cd C:\Users\MECHREVO\Desktop\排课系统\backend
.\.venv\Scripts\Activate
python -m uvicorn app.main:app --reload

# === 另一个终端，启动前端 ===
cd C:\Users\MECHREVO\Desktop\排课系统\frontend
npm run dev
```

### 修改代码后的检查清单

| 修改了什么 | 需要做什么 |
|-----------|-----------|
| Python 代码（.py） | 如果用了 --reload，会自动重启 |
| models.py（数据库模型） | 需要重置数据库：`python reset_db.py` |
| requirements.txt | 需要重新安装：`pip install -r requirements.txt` |
| Vue 代码（.vue/.js） | 如果用了 npm run dev，会自动刷新 |
| package.json | 需要重新安装：`npm install` |

### 环境管理黄金法则

1. **永远使用虚拟环境**，不要在全局 Python 安装项目依赖
2. **进入项目就激活**，确保 `(.venv)` 标记存在
3. **保持 requirements.txt 更新**，新安装库后运行 `pip freeze > requirements.txt`
4. **出问题先检查环境**，80% 的问题都是环境没配对

### 快速诊断命令

```powershell
# 我用的是哪个 Python？
where python

# 虚拟环境里装了哪些库？
pip list

# 当前在哪个目录？
pwd

# 后端服务在运行吗？（看有没有输出日志）
# 如果没有，重新启动：
python -m uvicorn app.main:app --reload
```

---

## 附录：术语表

| 术语 | 英文 | 解释 |
|-----|------|------|
| 虚拟环境 | Virtual Environment | Python 的隔离运行环境 |
| 包管理器 | Package Manager | 管理第三方库的工具（如 pip） |
| 依赖 | Dependency | 项目运行所需要的库 |
| 激活 | Activate | 切换到使用虚拟环境的 Python |
| 全局 | Global | 系统范围内共享的 |
| 模块 | Module | Python 代码的组织单位（一个 .py 文件就是一个模块） |
| 库/包 | Library/Package | 别人写好的、可复用的代码集合 |

---

## 问题求助检查清单

下次遇到问题时，按这个清单排查：

- [ ] 我在正确的目录吗？（应该在 backend 或 frontend）
- [ ] 虚拟环境激活了吗？（看命令行有没有 `.venv`）
- [ ] 后端服务在运行吗？（看终端有没有在输出日志）
- [ ] 前端服务在运行吗？（看浏览器能不能打开页面）
- [ ] 错误信息说了什么？（仔细阅读错误的第一行和最后几行）
- [ ] 最近改了什么？（改 models.py 要重置数据库）

---

*文档版本：1.0*  
*更新日期：2026-01-29*  
*适用于：排课系统项目*
