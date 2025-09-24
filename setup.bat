@echo off
echo ====================================
echo Legal Document Analyzer Setup
echo ====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Proceeding with setup...
echo.

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install requirements
echo Installing required packages...
pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

:: Install spaCy model
echo Installing spaCy English model...
python -m spacy download en_core_web_sm

if %errorlevel% neq 0 (
    echo WARNING: Failed to install spaCy model. You may need to install it manually.
)

echo.
echo ====================================
echo Setup completed successfully!
echo ====================================
echo.
echo Next steps:
echo 1. Configure Firebase in firebase_setup.py
echo 2. Update cookie password in cookie_manager.py
echo 3. Run: streamlit run main.py
echo.
echo To activate the virtual environment in future sessions:
echo call venv\Scripts\activate.bat
echo.
pause
