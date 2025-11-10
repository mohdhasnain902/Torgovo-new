"""
Development settings for Torgovo_new.
"""
from .base import *

# Override settings for development
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Additional apps for development
INSTALLED_APPS += [
    'debug_toolbar',
]

# Debug toolbar middleware (add at the top)
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

# Debug toolbar settings
INTERNAL_IPS = [
    '127.0.0.1',
]

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Database for development (can use SQLite for quick setup)
# Uncomment to use SQLite instead of PostgreSQL
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Logging in development
LOGGING['handlers']['console']['level'] = 'DEBUG'

# Celery broker for development
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously
CELERY_TASK_EAGER_PROPAGATES = True