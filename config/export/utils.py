# app_name/utils.py
import os
import subprocess
import datetime
import platform
from django.conf import settings
from .models import Backup

def avtomatik_backup():
    db_name = settings.DATABASES['default']['NAME']
    db_user = settings.DATABASES['default']['USER']
    db_password = settings.DATABASES['default']['PASSWORD']
    db_host = settings.DATABASES['default']['HOST'] or 'localhost'
    db_port = settings.DATABASES['default']['PORT'] or '5432'

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(settings.MEDIA_ROOT, 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    filename = f'solvey_backup_{timestamp}.sql'
    backup_file = os.path.join(backup_dir, filename)

    # pg_dump path-i müəyyən et (Linux və Windows üçün)
    if platform.system() == 'Windows':
        # Windows üçün PostgreSQL default path
        pg_dump_path = r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe'
        if not os.path.exists(pg_dump_path):
            # Alternativ path-ləri yoxla
            for version in ['17', '16', '15', '14', '13', '12']:
                alt_path = rf'C:\Program Files\PostgreSQL\{version}\bin\pg_dump.exe'
                if os.path.exists(alt_path):
                    pg_dump_path = alt_path
                    break
    else:
        # Linux üçün: pg_dump birbaşa PATH-dadır
        pg_dump_path = 'pg_dump'

    env = os.environ.copy()
    env['PGPASSWORD'] = db_password

    try:
        subprocess.run([
            pg_dump_path,
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-f', backup_file,
            db_name
        ], check=True, env=env, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # Xəta logla (Django logging istifadə et)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Backup xətası: {e.stderr if e.stderr else str(e)}")
        raise

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
