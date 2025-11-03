"""
ASGI config for crypto trading platform.
"""
import os
from django.core.asgi import get_asgi_application

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_trading_platform.settings.development')

application = get_asgi_application()