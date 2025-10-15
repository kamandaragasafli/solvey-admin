# app_name/utils.py
import os
import subprocess
import datetime
from django.conf import settings
from .models import Backup

def avtomatik_backup():
    db_name = settings.DATABASES['default']['NAME']
    db_user = settings.DATABASES['default']['USER']
    db_password = settings.DATABASES['default']['PASSWORD']
    db_host = settings.DATABASES['default']['HOST']
    db_port = settings.DATABASES['default']['PORT']

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    filename = f'solvey_backup_{timestamp}.sql'
    backup_file = os.path.join(backup_dir, filename)

    pg_dump_path = r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe'
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password

    subprocess.run([
        pg_dump_path,
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '-f', backup_file,
        db_name
    ], check=True, env=env)

    # Fayl ölçüsünü hesablamaq
    size_bytes = os.path.getsize(backup_file)
    size_mb = size_bytes / (1024 * 1024)
    size_str = f"{size_mb:.2f} MB"

    # Modelə qeyd et
    Backup.objects.create(
        ad='Həftəlik Avtomatik Backup',
        fayl=f'backups/{filename}',
        olcu=size_str
    )
