@echo off
echo ============================================
echo   SmartServe AI - Starting up
echo ============================================

IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

IF NOT EXIST dataset\food_demand.csv (
    echo Generating dataset...
    python dataset\generate_dataset.py
)

IF NOT EXIST models\smartserve_demand_model.pkl (
    echo Training model...
    python models\train_model.py
)

echo Starting Flask app on http://localhost:5000 ...
python app.py

pause
