"""
Django settings for restaurant project.
Base settings shared across all environments.
"""

from pathlib import Path
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
# decouple's config() reads BASE_DIR/.env (and real environment variables).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

with open(BASE_DIR / 'VERSION') as f:
    VERSION = f.read().strip()

# SECURITY WARNING: keep the secret key used in production secret!
# The default is for local development only; production.py requires a real key.
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'config.staticfiles.StaticFilesConfig',  # django.contrib.staticfiles, minus static/src/

    # Third party apps
    'adminsortable2',
    'django_ckeditor_5',
    'crispy_forms',
    'crispy_tailwind',
    'easy_thumbnails',
    'taggit',
    
    # Local apps
    'apps.core',
    'apps.menu',
    'apps.content',
    'apps.events',
    'apps.media',
    'apps.members',
    'apps.staff',
]

LOGIN_URL = '/staff/login/'

DEFAULT_FROM_EMAIL = 'SoHo Pittsburgh <noreply@sohopittsburgh.com>'
EMAIL_SUBJECT_PREFIX = ''

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'apps.core.context_processors.site_settings',
                'apps.core.context_processors.site_version',
                'apps.staff.permissions.staff_access',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cache — database-backed so it is shared across gunicorn workers.
# Used for form rate limiting (core.utils.is_throttled).
# One-time setup per database: python manage.py createcachetable
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
    },
}

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms with Tailwind
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# CKEditor Configuration
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['bold', 'italic', 'underline', '|',
                    'numberedList', 'bulletedList', '|',
                    'link', 'removeFormat'],
        'height': 200,
    },
    'newsletter': {
        'toolbar': [
            'heading', '|',
            'bold', 'italic', 'underline', '|',
            'numberedList', 'bulletedList', '|',
            'link', 'uploadImage', '|',
            'blockQuote', 'horizontalLine', '|',
            'removeFormat',
        ],
        'heading': {
            'options': [
                {'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph'},
                {'model': 'heading2', 'view': 'h2', 'title': 'Heading', 'class': 'ck-heading_heading2'},
                {'model': 'heading3', 'view': 'h3', 'title': 'Subheading', 'class': 'ck-heading_heading3'},
            ],
        },
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft', 'imageStyle:alignCenter', 'imageStyle:alignRight'],
        },
        'height': 420,
    },
}

CKEDITOR_5_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Easy Thumbnails
THUMBNAIL_ALIASES = {
    '': {
        'menu_thumb': {'size': (300, 300), 'crop': True},
        'menu_large': {'size': (800, 600), 'crop': 'smart'},
        'event_thumb': {'size': (400, 300), 'crop': True},
        'event_large': {'size': (1200, 800), 'crop': 'smart'},
    },
}

# Admin settings — server error (500) reports are emailed here in production.
# Restaurant name/phone/address live in the SiteSettings model, not settings.
ADMIN_EMAIL = config('ADMIN_EMAIL', default='')
ADMINS = [('SoHo Admin', ADMIN_EMAIL)] if ADMIN_EMAIL else []
