import os
from pathlib import Path
from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent # type: ignore

if(settings.DEBUG == True):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print(settings.DEBUG)
else:
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE'),
            'NAME': str(os.environ.get('DB_NAME')),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': str(os.environ.get('DB_PORT')),
            'USER': str(os.environ.get('DB_USER')),
            'PASSWORD': str(os.environ.get('DB_PASSWORD')),
        },
    }
    print('debug switched off in production')

# if str(os.environ.get('DJANGO_ENV')) == 'local':
    
# else:
    
    