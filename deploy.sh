#!/bin/bash

# Deployment script for Solvey Admin
# Usage: ./deploy.sh

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Navigate to project directory (adjust path as needed)
cd /path/to/solvey-admin/config  # Update this path to your server's project directory

# Pull latest changes from GitHub
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Activate virtual environment (if using one)
# source venv/bin/activate  # Uncomment if using virtual environment

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Restart the application server
echo "🔄 Restarting application server..."

# For systemd service (uncomment and adjust service name)
# sudo systemctl restart solvey-admin

# For gunicorn with supervisor (uncomment and adjust)
# sudo supervisorctl restart solvey-admin

# For manual gunicorn (uncomment and adjust)
# pkill -f gunicorn
# nohup gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 &

echo "✅ Deployment completed successfully!"

