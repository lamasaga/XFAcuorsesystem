@echo off
setlocal enableextensions enabledelayedexpansion

rem UTF-8 output (best effort)
chcp 65001 >nul 2>&1

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

if not exist "%BACKEND_DIR%\" (
  echo [ERROR] 未找到 backend 目录：%BACKEND_DIR%
  exit /b 1
)
if not exist "%FRONTEND_DIR%\" (
  echo [ERROR] 未找到 frontend 目录：%FRONTEND_DIR%
  exit /b 1
)

set "DO_INSTALL=0"
if /i "%~1"=="install" set "DO_INSTALL=1"
if /i "%~1"=="--install" set "DO_INSTALL=1"
if /i "%~1"=="-i" set "DO_INSTALL=1"

echo.
echo ==============================
echo  XFA Course Scheduling System
echo  Quick Start
echo ==============================
echo.
echo 用法：
echo   quick-start.bat
echo     - 默认模式：只在缺失时安装依赖
echo   quick-start.bat install
echo     - 强制安装/更新依赖
echo.

rem ---- Backend: ensure venv ----
if not exist "%VENV_PY%" (
  echo [Backend] 未检测到虚拟环境，正在创建：%VENV_DIR%
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] 找不到 python。请先安装 Python 3.10+ 并确保已加入 PATH。
    exit /b 1
  )
  pushd "%BACKEND_DIR%" || exit /b 1
  python -m venv ".venv"
  if errorlevel 1 (
    popd
    echo [ERROR] 创建虚拟环境失败。
    exit /b 1
  )
  popd
  set "DO_INSTALL=1"
)

if not exist "%BACKEND_DIR%\requirements.txt" (
  echo [ERROR] 未找到后端依赖文件：%BACKEND_DIR%\requirements.txt
  exit /b 1
)

if "%DO_INSTALL%"=="1" (
  echo [Backend] 安装依赖（pip install -r requirements.txt）
  "%VENV_PIP%" install -r "%BACKEND_DIR%\requirements.txt"
  if errorlevel 1 (
    echo [ERROR] 后端依赖安装失败。
    exit /b 1
  )
) else (
  echo [Backend] 跳过依赖安装（如需强制安装请使用：quick-start.bat install）
)

if not exist "%BACKEND_DIR%\.env" (
  echo [WARN] 未检测到 %BACKEND_DIR%\.env
  echo        请根据 README 配置 DATABASE_URL 等环境变量，否则后端可能无法连接数据库。
)

rem ---- Frontend: install deps if needed ----
where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 找不到 node。请先安装 Node.js 18+ 并确保已加入 PATH。
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 找不到 npm。请确认 Node.js 安装完整且 npm 可用。
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] 未找到前端 package.json：%FRONTEND_DIR%\package.json
  exit /b 1
)

if "%DO_INSTALL%"=="1" (
  echo [Frontend] 安装依赖（npm install）
  pushd "%FRONTEND_DIR%" || exit /b 1
  npm install
  if errorlevel 1 (
    popd
    echo [ERROR] 前端依赖安装失败。
    exit /b 1
  )
  popd
) else (
  if not exist "%FRONTEND_DIR%\node_modules\" (
    echo [Frontend] 未检测到 node_modules，正在安装依赖（npm install）
    pushd "%FRONTEND_DIR%" || exit /b 1
    npm install
    if errorlevel 1 (
      popd
      echo [ERROR] 前端依赖安装失败。
      exit /b 1
    )
    popd
  ) else (
    echo [Frontend] node_modules 已存在，跳过依赖安装
  )
)

rem ---- Start services in new windows ----
echo.
echo [Start] 启动后端（FastAPI / Uvicorn --reload）
start "XFA Backend" cmd /k ""cd /d "%BACKEND_DIR%" ^&^& "%VENV_PY%" -m uvicorn app.main:app --reload""

echo [Start] 启动前端（Vite dev）
start "XFA Frontend" cmd /k ""cd /d "%FRONTEND_DIR%" ^&^& npm run dev""

echo.
echo [OK] 已发起启动：
echo   后端文档： http://localhost:8000/docs
echo   前端页面： http://localhost:3000
echo.
echo 关闭服务：在各自窗口按 Ctrl+C
echo.
exit /b 0

