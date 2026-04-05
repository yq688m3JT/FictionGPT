@echo off
title NovelGPT Direct Control
setlocal enabledelayedexpansion

echo [Step 1] Cleaning up stale processes...
:: 强行杀死所有残留的 python 和 uvicorn 进程，释放 8000 端口
taskkill /f /im python.exe 2>nul
taskkill /f /im uvicorn.exe 2>nul

echo [Step 2] Checking dependencies...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
pip install pyyaml uvicorn[standard] fastapi sqlalchemy openai chromadb sentence-transformers pydantic aiofiles websockets python-multipart httpx rich >nul 2>&1

echo [Step 3] Starting Backend (CURRENT WINDOW)...
echo [Info] Please wait until you see "Uvicorn running on http://127.0.0.1:8000"
echo [Info] Then you can manually open the Frontend.

:: 启动前端在另一个窗口
start "NovelGPT-Frontend" cmd /c "cd frontend && npm run dev"

:: 后端在当前窗口启动，这样你能看到所有崩溃信息
uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
pause

...

echo.
echo All services are starting up! 
echo.
pause
