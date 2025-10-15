import os
import sys
import django


sys.path.append(r"C:\Users\User\Desktop\Solvey-admin")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


django.setup()

from export.utils import avtomatik_backup

if __name__ == "__main__":
    avtomatik_backup()
