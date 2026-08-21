import os
from pathlib import Path
from datetime import timedelta
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DJANGO_ENV') == 'LOCAL'

SECRET_KEY = 'g6qacxrqm8^k=6l%^c#7lcl#h82rf_lr+v^=78i4lppis(wwgu'

# if DEBUG:
#     SECRET_KEY = os.environ.get('LOCAL_SECRET_KEY')
# else:
#     SECRET_KEY = os.environ.get('PRODUCTION_SECRET_KEY')


if DEBUG:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3000',
    ]

    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:3001',
        'http://127.0.0.1:3000',
    ]

    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_DOMAIN = None

    CSRF_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = False

else:
    ALLOWED_HOSTS = [
        'honeste-backend.vercel.app',
        'cfidb-backend.vercel.app',
        'api.cfi.church',
    ]

    CORS_ALLOWED_ORIGINS = [
        'https://cfidb.com',
        'https://www.cfidb.com',
        'https://blog.cfi.church',
        'https://api.cfi.church',
    ]

    CSRF_TRUSTED_ORIGINS = [
        'https://cfidb.com',
        'https://www.cfidb.com',
        'https://blog.cfi.church',
        'https://api.cfi.church',
    ]

    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_DOMAIN = ".cfi.church"

    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_DOMAIN = ".cfi.church"

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-csrftoken",
]

# if DEBUG:
#    ALLOWED_HOSTS = [
#        '127.0.0.1', 
#        'localhost', 
#        'honeste-backend.vercel.app',
#     ] 
# else:
#     ALLOWED_HOSTS = [
#         'honeste-backend.vercel.app',
#         'cfidb-backend.vercel.app',
#         'api.cfi.church',
#     ]

    
# if DEBUG:
#     CORS_ALLOWED_ORIGINS = [
#         'http://localhost:3000',
#         'http://localhost:3001',
#         "http://127.0.0.1:3000",
#     ]
# else:
#     CORS_ALLOWED_ORIGINS = [
#         'https://cfidb.com',
#         'https://www.cfidb.com',
#         'https://blog.cfi.church',
#         'https://api.cfi.church',
#     ]
    
# CSRF_TRUSTED_ORIGINS = [
#     'https://cfidb.com',
#     'https://www.cfidb.com',
#     'https://blog.cfi.church',
#     'https://api.cfi.church',
# ]

# if DEBUG:
#     SESSION_COOKIE_SAMESITE = "None"
#     SESSION_COOKIE_SECURE = False
#     SESSION_COOKIE_DOMAIN = None

#     CSRF_COOKIE_SAMESITE = "Lax"
#     CSRF_COOKIE_SECURE = False
# else:
#     SESSION_COOKIE_SAMESITE = "None"
#     SESSION_COOKIE_SECURE = True

#     CSRF_COOKIE_SAMESITE = "None"
#     CSRF_COOKIE_SECURE = True
    

INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'cloudinary',
    'djoser',
    'drf_spectacular',
    'login_history',
    'imagekit',
    # 'easyaudit',
    'django_extensions',
    'apps',
    'apps.users',
    'apps.core',
    'apps.churches',
    'apps.bookkeeper',
    'apps.people',
    'apps.projects',
    'apps.posts',
    'apps.strategic',
    'apps.analyzer',
    'apps.reports',
    'apps.uploads',
    'apps.shared',
    'apps.examinations',
    'apps.jethro',
    'apps.scripture',
]

JETHRO_ENABLED = os.environ.get("JETHRO_ENABLED", "true").lower() == "true"
JETHRO_MODEL = os.environ.get("JETHRO_MODEL", "")
JETHRO_MOCK_MODE = os.environ.get("JETHRO_MOCK_MODE", "").lower() == "true"
if "JETHRO_MOCK_MODE" not in os.environ:
    JETHRO_MOCK_MODE = DEBUG and not bool(os.environ.get("OPENAI_API_KEY"))
JETHRO_MAX_OUTPUT_TOKENS = int(os.environ.get("JETHRO_MAX_OUTPUT_TOKENS", "1000"))
JETHRO_MAX_TOOL_ITERATIONS = int(os.environ.get("JETHRO_MAX_TOOL_ITERATIONS", "4"))
JETHRO_DAILY_USER_LIMIT = int(os.environ.get("JETHRO_DAILY_USER_LIMIT", "100"))
JETHRO_MAX_MESSAGE_LENGTH = int(os.environ.get("JETHRO_MAX_MESSAGE_LENGTH", "2000"))
JETHRO_CONTEXT_MESSAGE_LIMIT = int(os.environ.get("JETHRO_CONTEXT_MESSAGE_LIMIT", "12"))
JETHRO_MAX_TOOL_RESULT_CHARS = int(os.environ.get("JETHRO_MAX_TOOL_RESULT_CHARS", "12000"))
JETHRO_TITHE_DRAFT_TTL_MINUTES = int(
    os.environ.get("JETHRO_TITHE_DRAFT_TTL_MINUTES", "15")
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'apps.core.middleware.cookies.PrintCookiesMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'apps.core.middleware.jwt_refresh.JWTRefreshMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.users.middleware.last_active.LastActiveMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.current_user.CurrentUserMiddleware',
    # 'easyaudit.middleware.easyaudit.EasyAuditMiddleware',
]

ROOT_URLCONF = 'cfidb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cfidb.wsgi.application'

if DEBUG:
    print("LOCAL DB")

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    print("Production DB")
    DATABASES = {
        'default': {
            'ENGINE': str(os.environ.get('DB_ENGINE')),
            'NAME': str(os.environ.get('DB_NAME')),
            'HOST': str(os.environ.get('DB_HOST')),
            'PORT': str(os.environ.get('DB_PORT')),
            'USER': str(os.environ.get('DB_USER')),
            'PASSWORD': str(os.environ.get('DB_PASSWORD')),
            'CONN_MAX_AGE': 60,
        },
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.User'

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Harare'

USE_I18N = True

USE_TZ = True

# if DEBUG:
#     STATICFILES_DIRS = [
#         os.path.join(BASE_DIR, 'static/')
#     ]
# else:
#     STATIC_ROOT = os.path.join(BASE_DIR, 'static/')


CLOUDINARY_STORAGE = {
    'CLOUD_NAME': str(os.environ.get('CLOUDINARY_NAME')), 
    'API_KEY': str(os.environ.get('CLOUDINARY_API_KEY')), 
    'API_SECRET': str(os.environ.get('CLOUDINARY_API_SECRET')),
}

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

if not DEBUG:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'


# if not DEBUG:
#     STORAGES = {
#         'staticfiles': {
#             'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
#         },
#     }
   
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DEFAULT_FROM_EMAIL = 'CFI Support <support@cfi.church>'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        "apps.users.authentication.DynamicAuthentication",
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


DJOSER = {
    'LOGIN_FIELD': 'email',
    'PASSWORD_RESET_CONFIRM_RETYPE': True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'PASSWORD_RESET_CONFIRM_URL': 'password/reset/{uid}/{token}',
    'SEND_CONFIRMATION_EMAIL': True,
    'SET_PASSWORD_RETYPE': True,
    'USER_CREATE_PASSWORD_RETYPE': True,
    'EMAIL': {
        'confirmation': 'apps.users.mail.ConfirmationEmail',
        'password_reset': 'apps.users.mail.PasswordResetEmail',
        'password_changed_confirmation': 'apps.users.mail.PasswordChangedConfirmationEmail',
        'password_changed_reset': 'djoser.email.PasswordChangedResetEmail',
    },
    # 'SERIALIZERS': {
    #     'user': 'apps.users.serializers.ListUserSerializer',
    #     'current_user': 'apps.users.serializers.ListUserSerializer',
    # }
    "SERIALIZERS": {
        "user": "apps.users.serializers.CurrentUserSerializer",
        "current_user": "apps.users.serializers.CurrentUserSerializer",
    }
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": str(os.environ.get('JWT_SECRET_KEY')),
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    
    "AUTH_HEADER_TYPES": ("JWT",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "AUTH_COOKIE": "accessToken",
    "AUTH_COOKIE_REFRESH": "refreshToken",
    "AUTH_COOKIE_SECURE": not DEBUG,
    "AUTH_COOKIE_SAMESITE": "Lax",
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = str(os.environ.get('EMAIL_HOST'))
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False
EMAIL_HOST_USER = str(os.environ.get('EMAIL_HOST_USER'))
EMAIL_HOST_PASSWORD = str(os.environ.get('EMAIL_HOST_PASSWORD'))

if DEBUG:
    DOMAIN = 'localhost'
else:
    DOMAIN = 'cfiws.com'
    
SITE_NAME = 'CFI Workspace'



SPECTACULAR_SETTINGS = {
    "TITLE": "CFI Workspace API",
    "DESCRIPTION": "Backend API for managing church assemblies, members, attendance, finances, and reports for the CFI Workspace platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "CFI Workspace",
        "email": "support@cfiworkspace.com",
    },
}


# CBA

# Replace this with your actual student profile model.
EXAMINATIONS_STUDENT_MODEL = "examinations.CBAStudentReference"

# The unique field on the student profile used for PDF matching.
EXAMINATIONS_STUDENT_NUMBER_FIELD = "student_number"

# The field on the student profile that points to AUTH_USER_MODEL.
EXAMINATIONS_STUDENT_USER_FIELD = ""

EXAMINATIONS_PROCESS_IMPORTS_ASYNC = False
EXAMINATIONS_MAX_PDF_SIZE = 10 * 1024 * 1024

EXAMINATIONS_STUDENT_NUMBER_REGEX = (
    r"\b[A-Za-z]{1,4}(?:[\s-]*\d){5,}\b"
)


# Legacy CBA API
CBA_API_USERS_URL = os.getenv(
    "CBA_API_USERS_URL",
    "https://cba-backend.vercel.app/api/auth/users/",
)
CBA_API_TOKEN = os.getenv("CBA_API_TOKEN", "")
CBA_API_AUTH_SCHEME = os.getenv("CBA_API_AUTH_SCHEME", "Bearer")
CBA_API_TIMEOUT = 30
CBA_API_VERIFY_SSL = True
