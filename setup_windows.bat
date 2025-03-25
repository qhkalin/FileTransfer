@echo off
:: This script installs the requirements and runs the application on Windows

:: Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install requirements
echo Installing requirements...
pip install -r app_requirements.txt

:: Run the application
echo Starting SecureFileVault application...
python -m gunicorn --bind 0.0.0.0:5000 --reload main:app

:: Keep window open if there's an error
pause