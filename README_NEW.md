# Crypto Trading Platform

A comprehensive Django-based crypto trading platform with subscription management, custom trading bots, managed bot services, and TradingView webhook integration.

## Features

### Core Platform
- **User Management**: Secure user authentication with exchange API credentials
- **Subscription System**: Flexible subscription plans with usage limits
- **Trading Bots**: Custom and managed trading bot solutions
- **Exchange Integration**: Support for Binance, Bybit, Kraken, and MEXC
- **Webhook Security**: Secure TradingView webhook integration with rate limiting

### Subscription Plans
- **Custom Bot Plans**: For users who want to create and manage their own trading bots
- **Managed Bot Plans**: For users who want professional management with guaranteed returns
- **Usage Limits**: API calls, webhook requests, and concurrent bot limits
- **Trial Periods**: 7-day free trials for all plans

### Trading Features
- **Multi-Exchange Support**: Connect to multiple exchanges simultaneously
- **Real-time Trading**: Execute trades through secure API integrations
- **Performance Tracking**: Detailed analytics and profit/loss calculations
- **Risk Management**: Built-in stop-loss and take-profit mechanisms

### Webhook Integration
- **TradingView Compatible**: Direct integration with TradingView alerts
- **Secure Webhooks**: Secret token validation and rate limiting
- **Real-time Execution**: Instant trade execution from webhook signals
- **Error Handling**: Comprehensive logging and retry mechanisms

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- PostgreSQL (for local development)

### Development Setup

1. **Clone the repository**:
```bash
git clone https://github.com/your-org/crypto-trading-platform.git
cd crypto-trading-platform
```

2. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Run with Docker Compose (Development)**:
```bash
docker-compose -f docker-compose.dev.yml up --build
```

4. **Create database migrations**:
```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
```

5. **Create superuser**:
```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

6. **Create default subscription plans**:
```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py shell
>>> from subscriptions.utils import create_default_subscription_plans
>>> create_default_subscription_plans()
>>> exit()
```

7. **Access the application**:
   - API: http://localhost:8000/api/
   - Admin: http://localhost:8000/admin/
   - Health Check: http://localhost:8000/api/health/
   - API Documentation: http://localhost:8000/api/docs/

### Production Deployment

1. **Set up production environment variables**:
```bash
cp .env.example .env
# Update with production settings
```

2. **Build and run production containers**:
```bash
docker-compose up --build -d
```

3. **Run database migrations**:
```bash
docker-compose exec web python manage.py migrate
```

4. **Collect static files**:
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

5. **Create superuser**:
```bash
docker-compose exec web python manage.py createsuperuser
```

## API Documentation

Comprehensive API documentation is available in [API_DOCUMENTATION.md](./API_DOCUMENTATION.md).

### Key Endpoints

#### Authentication
- `POST /api/users/login/` - User login
- `POST /api/users/register/` - User registration
- `GET /api/users/profile/` - Get user profile

#### Subscriptions
- `GET /api/subscription-plans/` - List available plans
- `POST /api/subscriptions/` - Create subscription
- `GET /api/subscriptions/my-subscription/` - Get current subscription

#### Custom Bots
- `POST /api/custom-bot/webhook/generate/` - Generate webhook URL
- `POST /api/custom-bot/webhook/receive/{secret}/` - Receive TradingView webhooks

#### Managed Bots
- `GET /api/managed-bot/available/` - List available managed bots
- `POST /api/managed-bot/subscribe/` - Subscribe to managed bot
- `GET /api/managed-bot/performance/` - Get performance data

## TradingView Integration

### Setting Up Webhooks

1. **Create a webhook**:
```python
import requests

response = requests.post(
    'http://localhost:8000/api/custom-bot/webhook/generate/',
    headers={'Authorization': 'Token YOUR_API_TOKEN'},
    json={
        'pair_config_id': 1,
        'webhook_name': 'My BTC Strategy'
    }
)
webhook_data = response.json()
```

2. **Configure TradingView Alert**:
   - Create a strategy in TradingView
   - Add alert condition with webhook URL
   - Use the provided JSON template in the alert message

3. **Webhook JSON Template**:
```json
{
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "price": "{{close}}",
  "quantity": "{{strategy.order.contracts}}",
  "secret": "YOUR_WEBHOOK_SECRET"
}
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com

# Database
DB_NAME=crypto_trading
DB_USER=postgres
DB_PASSWORD=secure-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/0

# Webhook Security
WEBHOOK_SECRET_LENGTH=32
WEBHOOK_RATE_LIMIT=10

# Exchange APIs
BINANCE_API_URL=https://api.binance.com
BYBIT_API_URL=https://api.bybit.com
```

### Database Setup

The platform uses PostgreSQL as the primary database. For development:

```bash
# Create database
createdb crypto_trading_dev

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## Architecture

### Project Structure

```
crypto-trading-platform/
├── crypto_trading_platform/     # Django project
│   ├── settings/                # Environment-specific settings
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py                  # WSGI configuration
├── users/                       # User management app
│   ├── models.py               # User and UserProfile models
│   ├── views.py                # User API views
│   └── serializers.py          # User serializers
├── trading/                    # Trading app
│   ├── models.py               # Trading models (PairConfig, Order, etc.)
│   ├── bot_manager.py          # TradingManager class
│   └── bots/                   # Exchange-specific bot implementations
├── subscriptions/              # Subscription app
│   ├── models.py               # Subscription models
│   ├── utils.py                # Utility functions
│   └── api/                    # API views and serializers
└── static/                     # Static files
```

### Key Components

1. **TradingManager**: Central bot management system
2. **Webhook Security**: Secure TradingView integration
3. **Performance Tracking**: Real-time profit/loss calculations
4. **Subscription Limits**: Usage monitoring and enforcement
5. **Exchange Integration**: Multi-exchange API support

## Monitoring and Logging

### Application Logs
- **Django logs**: `/app/logs/django.log`
- **Webhook logs**: `/app/logs/webhooks.log`
- **Trading logs**: `/app/logs/trading.log`

### Monitoring Tools
- **Flower**: Celery task monitoring (http://localhost:5555)
- **Admin Panel**: Django admin interface
- **Health Checks**: `/api/health/` endpoint

### Performance Metrics
- API response times
- Webhook processing times
- Database query performance
- Trade execution success rates

## Security

### Authentication
- Token-based authentication
- API key encryption
- Secure credential storage

### Webhook Security
- Secret token validation
- Rate limiting (10 requests/minute)
- IP whitelisting support
- Request signature validation

### Data Protection
- Encrypted API credentials
- HTTPS enforcement
- SQL injection prevention
- XSS protection

## Testing

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test subscriptions
python manage.py test trading

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Test Coverage
- Model tests
- API endpoint tests
- Webhook processing tests
- Utility function tests
- Integration tests

## Deployment

### Production Checklist

1. **Security**:
   - [ ] Set production `SECRET_KEY`
   - [ ] Enable HTTPS
   - [ ] Configure CORS properly
   - [ ] Set up SSL certificates

2. **Database**:
   - [ ] Configure PostgreSQL with proper connection pooling
   - [ ] Set up database backups
   - [ ] Optimize database indexes

3. **Performance**:
   - [ ] Configure Redis caching
   - [ ] Set up CDN for static files
   - [ ] Configure monitoring

4. **Monitoring**:
   - [ ] Set up error tracking (Sentry)
   - [ ] Configure log aggregation
   - [ ] Set up uptime monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- **Documentation**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Issues**: GitHub Issues
- **Email**: support@yourdomain.com

## Changelog

### v1.0.0 (2025-01-01)
- Initial release
- Subscription management system
- Custom bot webhooks
- Managed bot services
- Multi-exchange support
- TradingView integration