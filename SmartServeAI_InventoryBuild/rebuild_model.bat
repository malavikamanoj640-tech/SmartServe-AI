@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo SmartServe AI - Rebuild Demand Model
echo ================================================
python -c "import sklearn; print('Installed scikit-learn:', sklearn.__version__); raise SystemExit(0 if sklearn.__version__ == '1.9.0' else 1)"
if errorlevel 1 (
  echo ERROR: SmartServe AI requires scikit-learn 1.9.0.
  echo Install it with: python -m pip install --upgrade scikit-learn==1.9.0
  pause
  exit /b 1
)
python models\train_model.py
if errorlevel 1 (
  echo Model training failed.
  pause
  exit /b 1
)
echo.
echo Model rebuilt successfully for scikit-learn 1.9.0.
pause
