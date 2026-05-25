# 本地生产构建 + 检查 dist 是否仍含 localhost:8001
# 用法: .\scripts\deploy-check.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Frontend = Join-Path $Root "frontend"

Set-Location $Frontend

Write-Host ">>> npm run build (production)..." -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$matches = Select-String -Path "dist\assets\*.js" -Pattern "localhost:8001" -SimpleMatch -ErrorAction SilentlyContinue
if ($matches) {
    Write-Host "FAIL: dist still contains localhost:8001. Do not deploy." -ForegroundColor Red
    $matches | ForEach-Object { Write-Host $_.Line }
    exit 1
}

Write-Host "OK: build done, no localhost:8001 in dist." -ForegroundColor Green
Write-Host "Deploy frontend\dist to server static root." -ForegroundColor Green
