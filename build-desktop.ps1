# Schedule System - Desktop Build
param(
    [switch]$Clean,
    [switch]$SkipBuild
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================"
Write-Host "  Schedule System - Desktop Build"
Write-Host "========================================"
Write-Host ""

if ($Clean) {
    Write-Host "[Clean] Removing old builds..." -ForegroundColor Yellow
    @("frontend/dist","backend/dist","backend/build","backend-dist","dist-electron") | ForEach-Object {
        $p = "$Root/$_"
        if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "  Removed: $_" }
    }
}

if (-not $SkipBuild) {
    Write-Host "[1/3] Building frontend..." -ForegroundColor Green
    Push-Location "$Root/frontend"
    & npm install --silent
    & npm run build
    Pop-Location
} else {
    Write-Host "[1/3] Skipping frontend build" -ForegroundColor Yellow
}

Write-Host "[2/3] Packaging backend (PyInstaller)..." -ForegroundColor Green
Push-Location "$Root/backend"
if (-not (Test-Path ".venv/Scripts/pyinstaller.exe")) {
    & .venv/Scripts/pip install -q pyinstaller
}
$piArgs = @("--noconfirm","--clean","--name","run_desktop","--onedir","--console","--collect-all","ortools")
$hidden = @(
    "uvicorn.logging","uvicorn.lifespan.on","uvicorn.lifespan.off",
    "sqlalchemy.dialects.sqlite","sqlalchemy.dialects.postgresql","psycopg2",
    "pydantic","pydantic_settings","fastapi","starlette",
    "httptools","websockets","h11","anyio","sniffio",
    "dotenv","openpyxl","app.core.compat",
    "app.modules.students","app.modules.students.models",
    "app.modules.alevel_subjects","app.modules.alevel_subjects.models",
    "app.modules.course_selections","app.modules.course_selections.models",
    "app.modules.course_classes","app.modules.course_classes.models"
)
foreach ($h in $hidden) { $piArgs += @("--hidden-import", $h) }
& .venv/Scripts/pyinstaller $piArgs run_desktop.py
Pop-Location

if (Test-Path "$Root/backend-dist") { Remove-Item -Recurse -Force "$Root/backend-dist" }
Copy-Item -Recurse "$Root/backend/dist/run_desktop" "$Root/backend-dist"
Write-Host "  Backend packaged: backend-dist/" -ForegroundColor Green

Write-Host "[3/3] Building Electron..." -ForegroundColor Green
Push-Location "$Root/electron-app"
& npm install --silent
& npm run build:win
Pop-Location

$installers = Get-ChildItem "$Root/dist-electron/*.exe" -ErrorAction SilentlyContinue
Write-Host ""
if ($installers) {
    Write-Host "Build complete! Installer:" -ForegroundColor Green
    $installers | ForEach-Object { Write-Host "  $($_.Name)" }
} else {
    Write-Host "Build complete, check dist-electron/" -ForegroundColor Yellow
}
Write-Host ""
Read-Host "Press Enter to exit"
