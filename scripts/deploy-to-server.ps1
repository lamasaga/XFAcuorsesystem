# Deploy schedule system to production server (full or incremental).
# Usage:
#   .\scripts\deploy-to-server.ps1              # restart backend + rebuild frontend (code via git pull on server)
#   .\scripts\deploy-to-server.ps1 -FullUpload  # sync code from local HEAD via git archive

param(
    [switch]$FullUpload
)

$ErrorActionPreference = "Stop"
$Key = "C:\Users\MECHREVO\.ssh\alevelinfo_ed25519"
$Host_ = "ubuntu@42.193.112.229"
$RemoteRoot = "/srv/schedule"
$RemoteFrontend = "$RemoteRoot/frontend"
$PublicUrl = "http://42.193.112.229:8080"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Invoke-RemoteBash([string]$Script) {
    $escaped = $Script -replace "'", "'\''"
    ssh -i $Key $Host_ "bash -lc '$escaped'"
}

if ($FullUpload) {
    Write-Host ">>> Full code sync via git archive ..." -ForegroundColor Cyan
    $tar = Join-Path $env:TEMP "xfa-deploy.tar"
    Set-Location $Root
    git archive -o $tar HEAD
    scp -i $Key $tar "${Host_}:/tmp/xfa-deploy.tar"
    Invoke-RemoteBash "set -e; tar -xf /tmp/xfa-deploy.tar -C $RemoteRoot; rm -f /tmp/xfa-deploy.tar"
} else {
    Write-Host ">>> Pull latest from GitHub on server ..." -ForegroundColor Cyan
    Invoke-RemoteBash "set -e; cd $RemoteRoot; git fetch origin; git checkout main; git pull origin main"
}

Write-Host ">>> Backend: migrate + deps + restart ..." -ForegroundColor Cyan
$backendCmd = "set -e; cd $RemoteRoot/backend; source .venv/bin/activate; pip install -r requirements.txt -q; python scripts/migrate_layer_scope.py; deactivate; sudo systemctl restart schedule.service; sleep 2; systemctl is-active schedule.service; curl -s -o /dev/null -w docs:%{http_code} http://127.0.0.1:8000/docs; echo"
Invoke-RemoteBash $backendCmd

Write-Host ">>> Frontend: build + verify no localhost:8001 ..." -ForegroundColor Cyan
$frontendCmd = "set -e; cd $RemoteFrontend; npm ci 2>/dev/null || npm install; npm run build; ! grep -r localhost:8001 dist/assets/*.js; sudo nginx -t; sudo systemctl reload nginx"
Invoke-RemoteBash $frontendCmd

Write-Host ">>> Done. Open $PublicUrl and hard-refresh (Ctrl+Shift+R)." -ForegroundColor Green
