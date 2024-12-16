@echo off

REM Chuyển tới thư mục dự án
cd C:\Users\Administrator\Codes\gsm-python

REM Kích hoạt môi trường ảo Python
call venv\Scripts\activate

REM Khởi động FastAPI
start cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000"

REM Chờ FastAPI khởi động
timeout /t 3 >nul

REM Khởi động ngrok
start cmd /k "ngrok http 8000"

REM Thông báo hoàn tất
echo FastAPI và ngrok đã được khởi động.
pause
