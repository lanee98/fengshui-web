@echo off
chcp 65001 >nul
echo ============================================================
echo   Immerse Home · 风水审查可视化平台
echo ============================================================
echo.
echo  启动地址: http://127.0.0.1:5000
echo  按 Ctrl+C 停止服务
echo.
"E:\fengshui-project\venv\Scripts\python.exe" "E:\fengshui-project\webapp\app.py"
pause
