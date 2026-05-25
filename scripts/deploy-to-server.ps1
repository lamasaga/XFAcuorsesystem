# Sync frontend API config to production server and rebuild dist.
# Usage: .\scripts\deploy-to-server.ps1

$ErrorActionPreference = "Stop"
$Key = "C:\Users\MECHREVO\.ssh\alevelinfo_ed25519"
$Host_ = "ubuntu@82.156.225.73"
$RemoteFrontend = "/srv/schedule/frontend"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host ">>> Upload frontend config and sources ..." -ForegroundColor Cyan
$files = @(
  "frontend\src\api\index.js|${RemoteFrontend}/src/api/index.js",
  "frontend\.env.production|${RemoteFrontend}/.env.production",
  "frontend\vite.config.js|${RemoteFrontend}/vite.config.js",
  "frontend\src\router\index.js|${RemoteFrontend}/src/router/index.js"
)
foreach ($pair in $files) {
  $parts = $pair -split '\|', 2
  scp -i $Key (Join-Path $Root $parts[0]) "${Host_}:$($parts[1])"
}

Write-Host ">>> Remote npm run build + verify ..." -ForegroundColor Cyan
ssh -i $Key $Host_ "cd ${RemoteFrontend} && npm run build && (grep -c localhost:8001 dist/assets/index*.js || true) && sudo nginx -t && sudo systemctl reload nginx"

Write-Host ">>> Done. Open http://82.156.225.73 and hard-refresh (Ctrl+Shift+R)." -ForegroundColor Green
