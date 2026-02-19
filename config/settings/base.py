"""
Django settings for restaurant project.
Base settings shared across all environments.
"""

from pathlib import Path
from decouple import config
import os
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# Build paths inside the project
#BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'adminsortable2',
    'django_ckeditor_5',
    'crispy_forms',
    'crispy_tailwind',
    'easy_thumbnails',

    # Local apps
    'apps.core',
    'apps.menu',
    'apps.promotions',
]

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
            BASE_DIR / 'themes',
        ],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'apps.core.context_processors.site_settings',
                'apps.core.context_processors.active_theme',
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
TIME_ZONE = 'UTC'
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

# Admin settings
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@restaurant.com')),
]

# Restaurant Settings (can be overridden in database via SiteSettings model)
RESTAURANT_NAME = config('RESTAURANT_NAME', default='Your Restaurant2')
RESTAURANT_PHONE = config('RESTAURANT_PHONE', default='')
RESTAURANT_EMAIL = config('RESTAURANT_EMAIL', default='')
RESTAURANT_ADDRESS = config('RESTAURANT_ADDRESS', default='')
