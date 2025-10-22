import os
import sys

# ABSOLUTE PATH - bu dəfə işləməli
sys.path.insert(0, '/var/www/solvey-admin')
sys.path.insert(0, '/var/www/solvey-admin/config')

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
