# Schedule System Quick Start
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$Root/backend'; .venv/Scripts/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"

# Frontend
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$Root/frontend'; npm run dev"

# Browser
Start-Sleep 3
Start-Process "http://localhost:3000"
