@echo off
chcp 65001 >nul
title 智农慧眼 - 一键启动

echo ========================================
echo   智农慧眼 AgriEye · 一键启动
echo ========================================
echo.

set BACKEND_DIR=%~dp0backend
set FRONTEND_DIR=%~dp0frontend

rem --- 检查 Python ---
echo [1/4] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python 未安装，请先安装 Python 3.10+
  pause
  exit /b 1
)

rem --- 检查 Node ---
echo [2/4] 检查 Node...
node --version >nul 2>&1
if errorlevel 1 (
  echo Node 未安装，请先安装 Node 18+
  pause
  exit /b 1
)

rem --- 检查端口 ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
  echo 端口 8001 已被进程 %%a 占用，尝试终止...
  taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
  echo 端口 5173 已被进程 %%a 占用，尝试终止...
  taskkill /F /PID %%a >nul 2>&1
)

rem --- 启动后端 ---
echo [3/4] 启动后端（FastAPI :8001）...
start "后端-智农慧眼" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

rem --- 启动前端 ---
echo [4/4] 启动前端（Vite :5173）...
start "前端-智农慧眼" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo ========================================
echo   启动完成！
echo   前端: http://localhost:5173
echo   后端: http://localhost:8001
echo   API文档: http://localhost:8001/docs
echo ========================================
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:5173