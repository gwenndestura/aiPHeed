@echo off
REM Starts the aiPHeed backend (port 8000) and frontend (port 5173) together, each in its own window,
REM then opens the thesis page. Close the two windows to stop them.
set ROOT=%~dp0
start "aiPHeed backend :8000" cmd /k "cd /d %ROOT%backend && python -m uvicorn app.main:app --port 8000 --reload"
start "aiPHeed frontend :5173" cmd /k "cd /d %ROOT%frontend && npx vite --port 5173"
timeout /t 8 /nobreak >nul
start "" http://localhost:5173/thesis
