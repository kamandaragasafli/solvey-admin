# Deployment Guide

## Server Deployment Steps

### 1. SSH into your server
```bash
ssh user@your-server-ip
```

### 2. Navigate to your project directory
```bash
cd /path/to/solvey-admin/config
```

### 3. Pull latest changes from GitHub
```bash
git pull origin main
```

### 4. Activate virtual environment (if using one)
```bash
source venv/bin/activate
# or
source /path/to/venv/bin/activate
```

### 5. Install/update dependencies
```bash
pip install -r requirements.txt
```

### 6. Collect static files
```bash
python manage.py collectstatic --noinput
```

### 7. Run database migrations
```bash
python manage.py migrate
```

### 8. Restart the application server

#### Option A: Using systemd service
```bash
sudo systemctl restart solvey-admin
# Check status
sudo systemctl status solvey-admin
```

#### Option B: Using supervisor
```bash
sudo supervisorctl restart solvey-admin
# Check status
sudo supervisorctl status solvey-admin
```

#### Option C: Manual gunicorn restart
```bash
# Find and kill existing gunicorn process
pkill -f gunicorn

# Start gunicorn (adjust settings as needed)
nohup gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 &
```

### 9. Verify deployment
```bash
# Check if the application is running
curl http://localhost:8000
# or visit your domain in a browser
```

## Quick Deploy Script

Make the deploy script executable:
```bash
chmod +x deploy.sh
```

Run the deployment:
```bash
./deploy.sh
```

## Environment Variables

Make sure your `.env` file or environment variables are set correctly on the server:
- `SECRET_KEY`
- `DEBUG=False` (for production)
- Database credentials
- Other required settings

## Troubleshooting

### If migrations fail:
```bash
python manage.py migrate --fake-initial
```

### If static files don't update:
```bash
python manage.py collectstatic --clear --noinput
```

### Check application logs:
```bash
# For systemd
sudo journalctl -u solvey-admin -f

# For supervisor
sudo tail -f /var/log/supervisor/solvey-admin.log

# For gunicorn
tail -f nohup.out
```

## Notes

- Always backup your database before deploying
- Test migrations on a staging environment first if possible
- Keep your server's Python and dependencies updated
- Monitor server resources (CPU, memory, disk space)

