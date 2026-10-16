#!/bin/bash

# release.sh - Deploy the Django application to production
# This script handles git operations, migrations, and static file collection

set -e

# Configuration
APP_NAME="apotheke"
REMOTE_USER=${REMOTE_USER:-root}
REMOTE_HOST=${REMOTE_HOST:-}
REMOTE_PATH=${REMOTE_PATH:-/var/www/$APP_NAME}
BRANCH=${BRANCH:-master}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting deployment of $APP_NAME ===${NC}"

# Check if remote host is set
if [ -z "$REMOTE_HOST" ]; then
    echo -e "${RED}Error: REMOTE_HOST environment variable not set${NC}"
    echo "Usage: REMOTE_HOST=your-server.com ./release.sh"
    exit 1
fi

# Step 1: Run tests locally (optional)
if [ "$RUN_TESTS" = "true" ]; then
    echo -e "${YELLOW}Running tests...${NC}"
    python manage.py test
fi

# Step 2: Git push
echo -e "${YELLOW}Pushing code to $BRANCH branch...${NC}"
git push origin $BRANCH

# Step 3: SSH into remote server and deploy
echo -e "${YELLOW}Deploying to $REMOTE_HOST...${NC}"

ssh $REMOTE_USER@$REMOTE_HOST << EOF
    set -e

    cd $REMOTE_PATH

    # Pull latest changes
    echo "Pulling latest changes..."
    git pull origin $BRANCH

    # Activate virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d "env" ]; then
        source env/bin/activate
    else
        echo "Error: Virtual environment not found"
        exit 1
    fi

    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt

    # Run migrations
    echo "Running migrations..."
    python manage.py migrate --noinput

    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    # Restart Gunicorn (using systemd)
    echo "Restarting Gunicorn..."
    sudo systemctl restart gunicorn
    sudo systemctl restart nginx

    echo "Deployment completed successfully!"
EOF

echo -e "${GREEN}=== Deployment completed successfully! ===${NC}"
