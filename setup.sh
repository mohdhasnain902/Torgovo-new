#!/bin/bash

# Torgovo_new Setup Script
echo "🚀 Setting up Torgovo_new - Crypto Trading Bot Platform"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs static media templates

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Django Configuration
SECRET_KEY=django-insecure-change-me-in-production-key-please
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
DB_NAME=torgovo_new_dev
DB_USER=postgres
DB_PASSWORD=devpassword
DB_HOST=localhost
DB_PORT=5432

# Security
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# CORS Settings
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1

# Webhook Security
WEBHOOK_SECRET_LENGTH=32
WEBHOOK_RATE_LIMIT=10
WEBHOOK_ALLOWED_IPS=

# Exchange API Settings
BINANCE_API_URL=https://api.binance.com
BINANCE_TESTNET_URL=https://testnet.binance.vision
BYBIT_API_URL=https://api.bybit.com
BYBIT_TESTNET_URL=https://api-testnet.bybit.com
KRAKEN_API_URL=https://api.kraken.com
MEXC_API_URL=https://api.mexc.com
MEXC_TESTNET_URL=https://api.testnet.mexc.com

# Trading Settings
MAX_ORDER_SIZE=10000.0
MIN_ORDER_SIZE=10.0
DEFAULT_LEVERAGE=1

# Field Encryption
FIELD_ENCRYPTION_KEY=django-insecure-field-key-please-change

# Application URLs
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Logging
LOG_LEVEL=INFO
ENABLE_FILE_LOGGING=True
EOF
    echo "✅ .env file created"
fi

echo "🔧 Installing Python dependencies..."
pip install -r requirements.txt

echo "🗄️  Running database migrations..."
python manage.py makemigrations

echo "🗄️  Applying database migrations..."
python manage.py migrate

echo "👤 Creating superuser..."
python manage.py createsuperuser

echo "🌱  Creating default subscription plans..."
python manage.py shell << EOF
from subscriptions.utils import create_default_subscription_plans
try:
    create_default_subscription_plans()
    print("✅ Default subscription plans created")
except Exception as e:
    print(f"⚠️  Error creating subscription plans: {e}")
exit()
EOF

echo "🎉 Setup complete!"
echo ""
echo "🚀 To start the development server:"
echo "   docker-compose -f docker-compose.dev.yml up"
echo ""
echo "🌐 Access the application at:"
echo "   http://localhost:8000/api/"
echo "   http://localhost:8000/admin/"
echo ""
echo "📚 API Documentation: ./API_DOCUMENTATION.md"
echo "📱 Frontend Documentation: ./FRONTEND_DOCUMENTATION.md"