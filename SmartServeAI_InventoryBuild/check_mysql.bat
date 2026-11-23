@echo off
echo ==========================================
echo SmartServe AI - MySQL Database Check
echo ==========================================
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -c "from database.db import ensure_database; ok,msg=ensure_database(); print(('READY: ' if ok else 'NOT READY: ') + msg)"
) else (
    python -c "from database.db import ensure_database; ok,msg=ensure_database(); print(('READY: ' if ok else 'NOT READY: ') + msg)"
)
pause
