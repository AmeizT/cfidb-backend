import os
from pathlib import Path
from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent # type: ignore

if(settings.DEBUG == False):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': str(os.environ.get('DB_ENGINE')),
            'NAME': str(os.environ.get('DB_NAME')),
            'HOST': str(os.environ.get('DB_HOST')),
            'PORT': str(os.environ.get('DB_PORT')),
            'USER': str(os.environ.get('DB_USER')),
            'PASSWORD': str(os.environ.get('DB_PASSWORD')),
        },
    }
    print('debug switched off in production')

# if str(os.environ.get('DJANGO_ENV')) == 'local':
    
# else:
    
    