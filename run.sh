#!/bin/bash

# run.sh - Run the Django application with Gunicorn
# This script is for local development or production with Gunicorn

set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
else
    echo "Error: Virtual environment not found (venv or env)"
    exit 1
fi

# Set default environment variables if not set
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-config.settings}
export DEBUG=${DEBUG:-0}
export ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost,127.0.0.1}

# Install dependencies if requirements.txt changed
if [ requirements.txt -nt venv/.last_install 2>/dev/null ] || [ ! -f venv/.last_install ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.last_install
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --threads 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
