from settings import *
import os


DEBUG = True
TEMPLATE_DEBUG = DEBUG
PROJECT_DIR = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
STATIC_DOC_ROOT = os.path.join('hk/media/')
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'dev.db'),
    }
}
