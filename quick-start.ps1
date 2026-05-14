# Schedule System Quick Start
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$Root/backend'; .venv/Scripts/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"

# Frontend
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$Root/frontend'; npm run dev"

# 等待后端就绪（轮询检测，最多 30 秒）
Write-Host ">>> 等待后端服务就绪..."
$maxWait = 30
$elapsed = 0
while ($elapsed -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/" -Method GET -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host ">>> 后端已就绪，正在打开浏览器..."
            break
        }
    } catch {
        # 后端尚未就绪，继续等待
    }
    Start-Sleep 1
    $elapsed++
}
if ($elapsed -ge $maxWait) {
    Write-Warning ">>> 后端启动超时，请手动刷新浏览器"
}

# Browser
Start-Process "http://localhost:3000"
