import os
import sys
import pathlib

# Ensure project root is on sys.path so `config` package is importable
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = 'temp_admin'
email = 'temp_admin@example.com'
password = 'TempPass123!'

u = User.objects.filter(username=username).first()
if not u:
    User.objects.create_superuser(username=username, email=email, password=password)
    print('CREATED:'+username)
else:
    u.set_password(password)
    u.is_superuser = True
    u.is_staff = True
    u.save()
    print('UPDATED:'+username)

print('USERNAME:', username)
print('PASSWORD: (hidden)')
