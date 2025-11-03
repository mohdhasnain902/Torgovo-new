"""
WSGI config for crypto trading platform.
"""
import os
from django.core.wsgi import get_wsgi_application

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_trading_platform.settings.development')

application = get_wsgi_application()