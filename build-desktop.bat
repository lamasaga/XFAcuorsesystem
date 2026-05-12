@echo off
chcp 65001 >nul
title 智能排课系统 - 桌面应用构建

echo ==========================================
echo   智能排课系统 - 桌面应用打包工具
echo ==========================================
echo.

REM -----------------------------------------
REM 第 0 步：检查环境
REM -----------------------------------------
echo [0/4] 检查构建环境...

python --version 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

node --version 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

echo       Python 和 Node.js 已就绪
echo.

REM 激活虚拟环境
if exist .venv\Scripts\activate.bat (
    echo [环境] 检测到虚拟环境，正在激活...
    call .venv\Scripts\activate.bat
    echo       虚拟环境已激活
) else (
    echo [警告] 未检测到 .venv 虚拟环境，将使用系统 Python
)
echo.

REM -----------------------------------------
REM 第 1 步：构建前端
REM -----------------------------------------
echo [1/4] 构建前端静态文件...
cd frontend
call npm install
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    cd ..
    pause
    exit /b 1
)
cd ..
echo       前端构建完成 (frontend/dist/)
echo.

REM -----------------------------------------
REM 第 2 步：打包后端为可执行文件
REM -----------------------------------------
echo [2/4] 使用 PyInstaller 打包后端...

cd backend

REM 确保安装了 PyInstaller
pip install pyinstaller -q

REM 使用绝对路径调用 pyinstaller，避免 PATH 问题
set "PYINSTALLER_EXE="

REM 优先尝试虚拟环境中的 pyinstaller
if exist "%~dp0.venv\Scripts\pyinstaller.exe" (
    set "PYINSTALLER_EXE=%~dp0.venv\Scripts\pyinstaller.exe"
    echo       使用虚拟环境中的 PyInstaller
) else (
    REM 回退到 PATH 中的 pyinstaller
    where pyinstaller >nul 2>&1
    if not errorlevel 1 (
        set "PYINSTALLER_EXE=pyinstaller"
        echo       使用系统 PATH 中的 PyInstaller
    ) else (
        echo [错误] 找不到 PyInstaller，请运行: pip install pyinstaller
        cd ..
        pause
        exit /b 1
    )
)

REM PyInstaller 打包
"%PYINSTALLER_EXE%" --noconfirm --clean ^
    --name run_desktop ^
    --onedir ^
    --console ^
    --collect-all ortools ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.http.h11_impl ^
    --hidden-import uvicorn.protocols.http.httptools_impl ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.protocols.websockets.wsproto_impl ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import uvicorn.lifespan.off ^
    --hidden-import ortools ^
    --hidden-import ortools.sat ^
    --hidden-import ortools.sat.python ^
    --hidden-import ortools.sat.python.cp_model ^
    --hidden-import sqlalchemy.dialects.sqlite ^
    --hidden-import pydantic ^
    --hidden-import pydantic_settings ^
    --hidden-import fastapi ^
    --hidden-import starlette ^
    --hidden-import httptools ^
    --hidden-import websockets ^
    --hidden-import h11 ^
    --hidden-import anyio ^
    --hidden-import sniffio ^
    --hidden-import dotenv ^
    --hidden-import app.core.compat ^
    run_desktop.py

if errorlevel 1 (
    echo [错误] 后端打包失败
    cd ..
    pause
    exit /b 1
)

cd ..

REM 复制打包结果到统一目录
if exist backend-dist rmdir /s /q backend-dist
xcopy /E /I /Q backend\dist\run_desktop backend-dist

echo       后端打包完成 (backend-dist/)
echo.

REM -----------------------------------------
REM 第 3 步：安装 Electron 依赖
REM -----------------------------------------
echo [3/4] 安装 Electron 构建依赖...
cd electron-app
call npm install
cd ..
echo       Electron 依赖安装完成
echo.

REM -----------------------------------------
REM 第 4 步：打包 Electron 应用
REM -----------------------------------------
echo [4/4] 打包 Electron 桌面应用...
cd electron-app
call npm run build:win
if errorlevel 1 (
    echo [错误] Electron 打包失败
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo ==========================================
echo   构建完成！
echo ==========================================
echo.
echo   安装包位置: dist-electron/
echo.
echo   请在 dist-electron 文件夹中找到
echo   .exe 安装程序，双击即可安装。
echo.
echo ==========================================
pause
