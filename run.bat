@echo off
REM run.bat - Run the Django application with Gunicorn on Windows
REM This script is for local development

setlocal enabledelayedexpansion

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
) else (
    echo Error: Virtual environment not found (venv or env)
    exit /b 1
)

REM Set default environment variables
if not defined DJANGO_SETTINGS_MODULE set DJANGO_SETTINGS_MODULE=config.settings
if not defined DEBUG set DEBUG=0
if not defined ALLOWED_HOSTS set ALLOWED_HOSTS=localhost,127.0.0.1

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run migrations
echo Running migrations...
python manage.py migrate --noinput

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput

REM Start development server (Gunicorn not recommended on Windows)
echo Starting Django development server...
python manage.py runserver 0.0.0.0:8000
