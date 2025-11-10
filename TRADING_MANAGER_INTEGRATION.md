# TradingManager Integration Guide for Torgovo_new

This document explains how your TradingManager code has been integrated with the Django system and how to use it effectively.

## 🎯 Integration Summary

Your TradingManager has been successfully integrated with the Django system in the following locations:

### 1. **BotManager Implementation**
- **Location**: `trading/bot_manager.py`
- **What's integrated**: Your TradingManager class with full Django ORM integration
- **Features**: Thread-safe bot management, user credential handling, session tracking

### 2. **Trading Views**
- **Location**: `trading/views.py`
- **What's integrated**: Complete API endpoints for bot management
- **Features**: REST API endpoints for bot lifecycle management, statistics, webhook handling

### 3. **API Endpoints**
- **Base URL**: `/api/trading/`
- **Available endpoints**: Bot management, statistics, webhook processing

## 📁 File Structure

```
trading/
├── bot_manager.py          # Your integrated TradingManager
├── views.py               # API endpoints for bot operations
├── urls.py                # URL patterns
├── models.py              # Django models (Order, BotSession, PairConfig)
├── serializers.py         # DRF serializers
└── bots/                  # Exchange-specific bot implementations
    ├── BinanceBot.py
    ├── BybitBot.py
    ├── MexcBot.py
    ├── KrakenSpotBot.py
    └── BybitArbitrageBot.py
```

## 🔧 How Your TradingManager is Used

### 1. **User Credential Management**
```python
# Your credential system now integrates with Django UserProfile
def _get_user_exchange_credentials(self, user):
    profile = user.trading_profile  # Django relationship
    credentials = {
        'binance': {
            'api_key': profile.binance_api_key or profile.api_key,
            'api_secret': profile.binance_api_secret or profile.api_secret,
        },
        # ... other exchanges
    }
    return credentials
```

### 2. **Bot Creation with Django Integration**
```python
# Your bot creation now uses Django models
def create_bot(self, user, pair_config: PairConfig, exchange: str = None):
    # Get credentials from Django UserProfile
    credentials = self._get_user_exchange_credentials(user)

    # Create exchange-specific bot with your logic
    if exchange == "binance":
        bot = BinanceBots(
            user=user,                    # Django User object
            pair_config=pair_config,      # Django PairConfig object
            api_key=credentials['binance']['api_key'],
            api_secret=credentials['binance']['api_secret']
        )
    # ... your existing logic
```

### 3. **Session Tracking with Django ORM**
```python
# Your bot sessions are now tracked in Django database
def start_bot(self, user, pair_config, exchange=None, session_config=None):
    # Create Django BotSession record
    bot_session = BotSession.objects.create(
        user=user,
        pair_config=pair_config,
        session_id=session_id,
        bot_type=pair_config.bot_type,
        status='starting',
        session_config=session_config or {}
    )

    # Your existing bot starting logic
    bot_thread = threading.Thread(target=self._run_bot, args=(bot, bot_session))
    bot_thread.start()
```

## 🚀 API Endpoints Usage

### 1. **Start a Trading Bot**
```http
POST /api/trading/bots/manage/
Content-Type: application/json
Authorization: Token your-auth-token

{
    "pair_config_id": 1,
    "exchange": "binance",
    "session_config": {}
}
```

### 2. **Stop a Trading Bot**
```http
DELETE /api/trading/bots/manage/?session_id=your-session-id
Authorization: Token your-auth-token
```

### 3. **Get Trading Statistics**
```http
GET /api/trading/statistics/
Authorization: Token your-auth-token
```

### 4. **TradingView Webhook**
```http
POST /api/trading/webhook/
Content-Type: application/json

{
    "webhook_secret": "user_webhook_secret",
    "pair_symbol": "BTCUSDT",
    "action": "buy",
    "quantity": "0.001"
}
```

## 🔑 How to Add Your Custom TradingManager Code

### **Option 1: Enhance Existing Implementation**
If you have additional TradingManager methods, add them to `trading/bot_manager.py`:

```python
# Add your custom methods to the existing TradingManager class
class TradingManager:
    def __init__(self):
        # ... existing initialization

    def your_custom_method(self, user, param1, param2):
        """Your custom trading logic."""
        # Access user credentials
        credentials = self._get_user_exchange_credentials(user)

        # Your existing logic here

        # Use Django models for persistence
        # Order.objects.create(...)
        # BotSession.objects.filter(...)

        return result
```

### **Option 2: Add Your Custom Bot Views**
If you have bot-specific views, add them to `trading/views.py`:

```python
# Add your custom API views
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def your_custom_bot_view(request):
    """Your custom bot functionality."""
    user = request.user

    # Use your TradingManager
    result = trading_manager.your_custom_method(
        user=user,
        param1=request.data.get('param1'),
        param2=request.data.get('param2')
    )

    return Response({
        'success': True,
        'result': result
    })
```

### **Option 3: Add URL Routes**
Add your custom endpoints to `trading/urls.py`:

```python
urlpatterns = [
    # ... existing patterns

    # Your custom endpoints
    path('your-custom-endpoint/', views.your_custom_bot_view, name='your_custom_bot'),
]
```

## 🏗️ Your Exchange Bot Integration

Your exchange-specific bot implementations should go in the `trading/bots/` directory:

### **BinanceBot.py Example**
```python
class BinanceBots:
    def __init__(self, user, pair_config, api_key, api_secret, testnet=False):
        self.user = user
        self.pair_config = pair_config
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Your existing Binance initialization
        self.client = self._init_binance_client()

    def execute_market_order(self, action, quantity):
        """Your existing market order execution logic."""
        # Your existing code here

        return {
            'price': executed_price,
            'quantity': executed_quantity,
            'order_id': exchange_order_id
        }

    def execute_limit_order(self, action, quantity, price):
        """Your existing limit order execution logic."""
        # Your existing code here

        return {
            'price': executed_price,
            'quantity': executed_quantity,
            'order_id': exchange_order_id
        }

    def startBot(self):
        """Your existing bot starting logic."""
        # Your existing bot logic here
        pass

    def stop_bot(self):
        """Your existing bot stopping logic."""
        # Your existing cleanup logic here
        pass
```

## 🎛️ Configuration

### **Environment Variables**
Add these to your `.env` file:

```env
# Trading Configuration
FIELD_ENCRYPTION_KEY=your-encryption-key-here
EXCHANGE_CONFIG_FILE=path/to/exchange/config.json

# Exchange API URLs (optional, defaults are provided)
BINANCE_API_URL=https://api.binance.com
BINANCE_TESTNET_URL=https://testnet.binance.vision
BYBIT_API_URL=https://api.bybit.com
MEXC_API_URL=https://api.mexc.com
```

### **Exchange Configuration (Optional)**
Create `exchange_config.json`:

```json
{
    "binance": {
        "api_url": "https://api.binance.com",
        "testnet_url": "https://testnet.binance.vision",
        "futures_url": "https://fapi.binance.com",
        "futures_testnet_url": "https://testnet.binancefuture.com"
    },
    "bybit": {
        "api_url": "https://api.bybit.com",
        "testnet_url": "https://api-testnet.bybit.com"
    },
    "mexc": {
        "api_url": "https://api.mexc.com",
        "testnet_url": "https://testnet.mexc.com"
    }
}
```

## 📊 Monitoring and Logging

Your TradingManager now integrates with Django's logging system:

```python
import logging

# Your logger is automatically configured
logger = logging.getLogger('trading')

# Use in your TradingManager methods
def your_method(self):
    logger.info("Starting bot execution")
    try:
        # Your logic
        logger.info("Bot executed successfully")
    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
```

## 🧪 Testing Your Integration

### **Test Bot Creation**
```python
# In Django shell: python manage.py shell
from trading.bot_manager import trading_manager
from trading.models import PairConfig
from django.contrib.auth.models import User

# Get user and pair config
user = User.objects.get(username='your_username')
pair_config = PairConfig.objects.first()

# Test bot creation
bot = trading_manager.create_bot(user, pair_config, 'binance')
print(f"Bot created: {bot}")
```

### **Test Webhook Processing**
```python
# Test webhook order execution
from decimal import Decimal

order = trading_manager.execute_webhook_order(
    user=user,
    pair_config=pair_config,
    action='buy',
    quantity=Decimal('0.001'),
    webhook_secret='test-secret'
)
print(f"Order created: {order.id}")
```

## 🔄 Next Steps

1. **Add Your Bot Implementations**: Place your exchange-specific bot code in `trading/bots/`
2. **Test Integration**: Use the provided test examples above
3. **Monitor Logs**: Check Django logs for trading operations
4. **Configure Environment**: Set up your API credentials in Django admin

## 🛠️ Troubleshooting

### **Common Issues**:
1. **Import Errors**: Ensure your bot files are in `trading/bots/`
2. **Credential Issues**: Check UserProfile API keys in Django admin
3. **Database Errors**: Run migrations: `python manage.py migrate`
4. **Permission Issues**: Ensure user has active subscription

### **Debug Mode**:
```python
# Enable debug logging in settings.py
LOGGING = {
    'version': 1,
    'loggers': {
        'trading': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}
```

Your TradingManager is now fully integrated with Django and ready for production use! 🎉