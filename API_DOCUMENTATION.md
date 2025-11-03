# Crypto Trading Platform API Documentation

## Overview

This API provides endpoints for a comprehensive crypto trading platform with subscription management, custom trading bots, managed bot services, and TradingView webhook integration.

**Base URL**: `https://yourdomain.com/api`
**API Version**: `1.0.0`
**Authentication**: Token-based (Bearer Token)

## Authentication

All protected endpoints require authentication using Django REST Framework Token Authentication.

### Getting Authentication Token

**Request**:
```bash
curl -X POST https://yourdomain.com/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response**:
```json
{
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "message": "Login successful"
}
```

### Using the Token

Include the token in the `Authorization` header for all subsequent requests:
```bash
curl -X GET https://yourdomain.com/api/subscription-plans/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

## Subscription Management

### 1. List Subscription Plans

Get all available subscription plans (public endpoint).

**Endpoint**: `GET /api/subscription-plans/`

**Parameters** (optional):
- `plan_type` - Filter by plan type (`custom_bot` or `managed_bot`)

**Request**:
```bash
curl -X GET https://yourdomain.com/api/subscription-plans/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "count": 4,
  "results": [
    {
      "id": 1,
      "plan_type": "custom_bot",
      "plan_type_display": "Custom Bot",
      "name": "Custom Bot Basic",
      "description": "Perfect for beginners getting started with automated trading",
      "features": {
        "max_trading_pairs": 3,
        "concurrent_bots": 2,
        "indicators": ["RSI", "MACD", "Bollinger Bands"],
        "backtesting": true,
        "basic_analytics": true
      },
      "monthly_price": "29.99",
      "yearly_price": null,
      "setup_fee": "0.00",
      "max_trading_pairs": 3,
      "max_bots": 2,
      "api_calls_per_day": 1000,
      "webhook_requests_per_hour": 50,
      "concurrent_bots": 2,
      "is_active": true,
      "is_public": true,
      "is_featured": false,
      "subscriber_count": 25,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### 2. Create Subscription

Subscribe to a plan.

**Endpoint**: `POST /api/subscriptions/`

**Request**:
```bash
curl -X POST https://yourdomain.com/api/subscriptions/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 1,
    "billing_cycle": "monthly",
    "auto_renew": true,
    "payment_method": "stripe"
  }'
```

**Response** (201 Created):
```json
{
  "id": 123,
  "user": {
    "id": 1,
    "username": "your_username"
  },
  "plan": {
    "id": 1,
    "name": "Custom Bot Basic",
    "plan_type": "custom_bot"
  },
  "status": "trial",
  "status_display": "Trial",
  "billing_cycle": "monthly",
  "billing_cycle_display": "Monthly",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-08T00:00:00Z",
  "trial_end_date": "2025-01-08T00:00:00Z",
  "auto_renew": true,
  "is_active_trial": true,
  "is_currently_active": true,
  "days_remaining": 7,
  "usage_stats": {
    "api_calls_used": 0,
    "api_calls_limit": 1000,
    "api_calls_remaining": 1000,
    "webhook_requests_used": 0,
    "webhook_requests_limit": 50,
    "webhook_requests_remaining": 50
  },
  "created_at": "2025-01-01T10:30:00Z"
}
```

### 3. Get My Subscription

Get current user's active subscription.

**Endpoint**: `GET /api/subscriptions/my-subscription/`

**Request**:
```bash
curl -X GET https://yourdomain.com/api/subscriptions/my-subscription/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "id": 123,
  "user": {
    "id": 1,
    "username": "your_username"
  },
  "plan": {
    "id": 1,
    "name": "Custom Bot Basic",
    "plan_type": "custom_bot"
  },
  "status": "active",
  "days_remaining": 30,
  "usage_stats": {
    "api_calls_used": 245,
    "api_calls_limit": 1000,
    "api_calls_remaining": 755,
    "webhook_requests_used": 12,
    "webhook_requests_limit": 50,
    "webhook_requests_remaining": 38
  }
}
```

### 4. Update Subscription

Update subscription settings (cancel, change auto_renew).

**Endpoint**: `PATCH /api/subscriptions/{id}/`

**Request**:
```bash
curl -X PATCH https://yourdomain.com/api/subscriptions/123/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "auto_renew": false,
    "status": "cancelled"
  }'
```

**Response**:
```json
{
  "id": 123,
  "auto_renew": false,
  "status": "cancelled"
}
```

### 5. Cancel Subscription

Cancel subscription immediately.

**Endpoint**: `POST /api/subscriptions/{subscription_id}/cancel/`

**Request**:
```bash
curl -X POST https://yourdomain.com/api/subscriptions/123/cancel/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "message": "Subscription cancelled successfully",
  "cancellation_date": "2025-01-15T10:30:00Z"
}
```

## Custom Bot Webhooks

### 1. Generate Webhook

Create a new webhook for custom bot integration with TradingView.

**Endpoint**: `POST /api/custom-bot/webhook/generate/`

**Request**:
```bash
curl -X POST https://yourdomain.com/api/custom-bot/webhook/generate/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pair_config_id": 5,
    "webhook_name": "My BTC Strategy",
    "allow_ip_whitelist": false,
    "require_signature": false
  }'
```

**Response** (201 Created):
```json
{
  "id": 789,
  "user": {
    "id": 1,
    "username": "your_username"
  },
  "subscription": {
    "id": 123,
    "plan": {
      "name": "Custom Bot Basic"
    }
  },
  "pair_config": {
    "id": 5,
    "name": "BTC/USDT Momentum",
    "pair_symbol": "BTCUSDT",
    "exchange": "binance"
  },
  "webhook_name": "My BTC Strategy",
  "webhook_url": "https://yourdomain.com/api/custom-bot/webhook/receive/abc123xyz456def/",
  "webhook_secret": "abc123xyz456def",
  "tradingview_config": {
    "webhook_url": "https://yourdomain.com/api/custom-bot/webhook/receive/abc123xyz456def/",
    "tradingview_json": {
      "action": "{{strategy.order.action}}",
      "ticker": "{{ticker}}",
      "price": "{{close}}",
      "quantity": "{{strategy.order.contracts}}",
      "secret": "abc123xyz456def"
    }
  },
  "is_active": true,
  "total_triggers": 0,
  "successful_triggers": 0,
  "success_rate": 0,
  "created_at": "2025-01-01T10:30:00Z"
}
```

### 2. Receive TradingView Webhook

This endpoint receives alerts from TradingView and executes trades.

**Endpoint**: `POST /api/custom-bot/webhook/receive/{webhook_secret}/`

**Security Features**:
- Webhook secret validation
- Rate limiting (10 requests/minute per webhook)
- IP whitelisting support
- Request logging for debugging

**Expected Payload from TradingView**:
```json
{
  "action": "buy",
  "ticker": "BTCUSDT",
  "price": "45000.50",
  "quantity": "0.01",
  "secret": "abc123xyz456def"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "BUY order executed successfully",
  "order_id": "123e4567-e89b-12d3-a456-426614174000",
  "order_details": {
    "action": "buy",
    "pair": "BTCUSDT",
    "quantity": "0.01000000",
    "price": "45000.50000000",
    "executed_price": "45000.50000000"
  },
  "processing_time_ms": 124.5
}
```

**Error Responses**:
- **401 Unauthorized**: Invalid webhook_secret
- **400 Bad Request**: Invalid payload format
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Trading execution failed

### 3. Test Webhook

Test webhook connectivity without executing trades.

**Endpoint**: `GET /api/custom-bot/webhook/test/{webhook_secret}/`

**Request**:
```bash
curl -X GET https://yourdomain.com/api/custom-bot/webhook/test/abc123xyz456def/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "status": "success",
  "webhook": {
    "id": 789,
    "name": "My BTC Strategy",
    "pair_config": {
      "symbol": "BTCUSDT",
      "exchange": "binance"
    },
    "is_active": true,
    "total_triggers": 25,
    "successful_triggers": 24,
    "last_triggered": "2025-01-01T09:45:00Z"
  }
}
```

## TradingView Integration Guide

### Setting Up TradingView Alerts

1. **Create a Strategy in TradingView Pine Script**:
```pinescript
//@version=5
strategy("My Trading Strategy", overlay=true)

// Your trading logic here
longCondition = ta.crossover(ta.sma(close, 14), ta.sma(close, 28))
if (longCondition)
    strategy.entry("My Long Entry Id", strategy.long)

shortCondition = ta.crossunder(ta.sma(close, 14), ta.sma(close, 28))
if (shortCondition)
    strategy.entry("My Short Entry Id", strategy.short)
```

2. **Add Alert Condition**:
   - **When**: Strategy entry/exit signals
   - **Action**: Webhook URL
   - **Message**: Use the provided JSON template from webhook generation

3. **Alert JSON Template** (generated by the API):
```json
{
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "price": "{{close}}",
  "quantity": "{{strategy.order.contracts}}",
  "secret": "abc123xyz456def"
}
```

### Supported TradingView Variables

- `{{strategy.order.action}}` - "buy" or "sell"
- `{{ticker}}` - Trading pair symbol (e.g., "BTCUSDT")
- `{{close}}` - Current closing price
- `{{strategy.order.contracts}}` - Order quantity
- `{{time}}` - Timestamp of signal
- `{{strategy.order.comment}}` - Custom order notes

### Trading Flow

1. User creates webhook in platform
2. Webhook URL and secret are generated
3. User configures TradingView alert with webhook URL
4. TradingView sends JSON payload to webhook URL
5. Platform validates webhook and executes trade
6. Order is executed through exchange API
7. Order status and performance are tracked

## Managed Bot Services

### 1. Available Managed Bots

List available managed bots with performance statistics.

**Endpoint**: `GET /api/managed-bot/available/`

**Parameters** (optional):
- `exchange` - Filter by exchange
- `pair` - Filter by trading pair
- `strategy` - Filter by strategy type

**Request**:
```bash
curl -X GET https://yourdomain.com/api/managed-bot/available/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "name": "BTC Momentum Bot",
      "pair_symbol": "BTCUSDT",
      "exchange": "binance",
      "strategy_type": "momentum",
      "description": "High-frequency BTC trading using momentum indicators",
      "performance_30d": "15.5",
      "performance_90d": "45.2",
      "total_subscribers": 125,
      "min_investment": "1000.00",
      "profit_share_percentage": "25.0",
      "guaranteed_monthly_return": "5.0"
    }
  ]
}
```

### 2. Subscribe to Managed Bot

Subscribe to a managed bot with investment amount.

**Endpoint**: `POST /api/managed-bot/subscribe/`

**Request**:
```bash
curl -X POST https://yourdomain.com/api/managed-bot/subscribe/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "managed_bot_id": 1,
    "initial_investment": "5000.00"
  }'
```

**Response** (201 Created):
```json
{
  "performance": {
    "id": 101,
    "user": {
      "id": 1,
      "username": "your_username"
    },
    "subscription": {
      "id": 123,
      "plan": {
        "name": "Managed Bot Premium"
      }
    },
    "managed_bot": {
      "id": 1,
      "name": "BTC Momentum Bot",
      "pair_symbol": "BTCUSDT",
      "exchange": "binance"
    },
    "initial_investment": "5000.00",
    "current_balance": "5000.00",
    "net_return": "0.00",
    "net_return_percentage": "0.0000",
    "profit_share_remaining": "0.00",
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "win_rate": "0.00",
    "created_at": "2025-01-01T10:30:00Z"
  },
  "session_id": "abc123def456",
  "message": "Successfully subscribed to managed bot"
}
```

### 3. Managed Bot Performance

Get user's managed bot performance and P&L data.

**Endpoint**: `GET /api/managed-bot/performance/`

**Parameters** (optional):
- `period_days` - Performance period in days (default: 30)
- `bot_id` - Specific bot ID

**Request**:
```bash
curl -X GET https://yourdomain.com/api/managed-bot/performance/?period_days=30 \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "summary": {
    "period_days": 30,
    "total_invested": "10000.00",
    "current_value": "11500.00",
    "total_profit": "1500.00",
    "total_loss": "200.00",
    "net_profit": "1300.00",
    "profit_percentage": "13.0000",
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": "62.22",
    "bot_breakdown": [
      {
        "bot_name": "BTC Momentum Bot",
        "initial_investment": "5000.00",
        "current_balance": "5750.00",
        "net_profit": "750.00",
        "profit_percentage": "15.0000"
      }
    ]
  },
  "bots": [
    {
      "id": 101,
      "managed_bot": {
        "id": 1,
        "name": "BTC Momentum Bot",
        "pair_symbol": "BTCUSDT",
        "exchange": "binance"
      },
      "initial_investment": "5000.00",
      "current_balance": "5750.00",
      "total_profit": "800.00",
      "total_loss": "50.00",
      "net_profit": "750.00",
      "profit_percentage": "15.0000",
      "net_return": "750.00",
      "net_return_percentage": "15.0000",
      "profit_share_paid": "0.00",
      "profit_share_remaining": "187.50",
      "total_trades": 23,
      "winning_trades": 15,
      "losing_trades": 8,
      "win_rate": "65.22"
    }
  ],
  "period_days": 30
}
```

### 4. Managed Bot Rankings

Get ranked list of managed bots by performance.

**Endpoint**: `GET /api/managed-bot/rankings/`

**Parameters** (optional):
- `period_days` - Ranking period in days (default: 30)

**Request**:
```bash
curl -X GET https://yourdomain.com/api/managed-bot/rankings/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "period_days": 30,
  "rankings": [
    {
      "bot_id": 1,
      "bot_name": "BTC Momentum Bot",
      "pair_symbol": "BTCUSDT",
      "exchange": "binance",
      "strategy_type": "momentum",
      "total_subscribers": 125,
      "total_invested": "125000.00",
      "avg_performance": "15.2500",
      "total_trades": 2850
    }
  ]
}
```

## User Management

### 1. User Registration

Register a new user account.

**Endpoint**: `POST /api/users/register/`

**Request**:
```bash
curl -X POST https://yourdomain.com/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_user",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "securepassword123",
    "password_confirm": "securepassword123"
  }'
```

**Response** (201 Created):
```json
{
  "user": {
    "id": 2,
    "username": "new_user",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe"
  },
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "message": "User registered successfully"
}
```

### 2. User Profile

Get current user's profile and trading information.

**Endpoint**: `GET /api/users/profile/`

**Request**:
```bash
curl -X GET https://yourdomain.com/api/users/profile/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "id": 1,
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "user@example.com"
  },
  "exchange": "binance",
  "exchange_display": "Binance",
  "demo_mode": true,
  "timezone": "Asia/Karachi",
  "leverage": 1,
  "max_position_size": "1000.00",
  "email_notifications": true,
  "trade_notifications": true,
  "profit_loss_notifications": true,
  "max_daily_loss": "100.00",
  "stop_loss_percentage": "5.00",
  "take_profit_percentage": "10.00",
  "created_at": "2025-01-01T00:00:00Z",
  "is_active_trader": true,
  "total_traded_volume": "25000.00",
  "profit_loss_summary": {
    "total_buy_value": "12000.00",
    "total_sell_value": "12500.00",
    "gross_profit": "500.00",
    "total_orders": 15,
    "buy_orders": 8,
    "sell_orders": 7
  }
}
```

### 3. Update Exchange Credentials

Update exchange API credentials for trading.

**Endpoint**: `PUT /api/users/profile/`

**Request**:
```bash
curl -X PUT https://yourdomain.com/api/users/profile/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "api_key": "your_api_key_here",
    "api_secret": "your_api_secret_here",
    "demo_mode": true
  }'
```

**Response**:
```json
{
  "id": 1,
  "exchange": "binance",
  "demo_mode": true,
  "updated_at": "2025-01-01T12:00:00Z"
}
```

## Usage Monitoring

### 1. Subscription Usage

Get current subscription usage statistics.

**Endpoint**: `GET /api/subscriptions/usage/`

**Request**:
```bash
curl -X GET https://yourdomain.com/api/subscriptions/usage/ \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response**:
```json
{
  "api_calls_used": 245,
  "api_calls_limit": 1000,
  "api_calls_remaining": 755,
  "webhook_requests_used": 12,
  "webhook_requests_limit": 50,
  "webhook_requests_remaining": 38,
  "bots_used": 2,
  "bots_limit": 3,
  "pairs_used": 2,
  "pairs_limit": 3
}
```

## Error Handling

### Standard Error Response Format

All error responses follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Specific field error (if applicable)",
      "value": "Invalid value (if applicable)"
    }
  }
}
```

### Common HTTP Status Codes

- **200 OK** - Request successful
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Authentication required or failed
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **409 Conflict** - Resource conflict (duplicate, etc.)
- **422 Unprocessable Entity** - Validation failed
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

### Rate Limiting

- **API Endpoints**: 100 requests per hour per authenticated user
- **Webhook Endpoints**: 10 requests per minute per webhook_secret

Rate limit headers are included in responses:
- `X-RateLimit-Limit` - Request limit per window
- `X-RateLimit-Remaining` - Remaining requests in current window
- `X-RateLimit-Reset` - Time when limit resets (Unix timestamp)

## Webhook Security

### Security Features

1. **Secret Token Validation**: Each webhook has a unique secret
2. **Rate Limiting**: 10 requests per minute per webhook
3. **IP Whitelisting**: Optional IP address restriction
4. **Request Logging**: All webhook requests are logged
5. **Signature Validation**: Optional HMAC-SHA256 signature support

### Best Practices

1. **Keep Secrets Secure**: Never expose webhook secrets in client-side code
2. **Monitor Logs**: Regularly review webhook request logs
3. **Use HTTPS**: Always send webhook requests over HTTPS
4. **Test Thoroughly**: Use the test endpoint before going live
5. **Handle Failures**: Implement retry logic for failed requests

## Pagination

List endpoints support pagination with these parameters:

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

**Example Request**:
```bash
curl -X GET "https://yourdomain.com/api/subscriptions/?page=2&page_size=10" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Response Format**:
```json
{
  "count": 45,
  "next": "https://yourdomain.com/api/subscriptions/?page=3",
  "previous": "https://yourdomain.com/api/subscriptions/?page=1",
  "results": [...]
}
```

## WebSocket Support (Future Feature)

Real-time updates will be available via WebSocket connections at `wss://yourdomain.com/ws/updates/`

Supported channels:
- `orders` - Real-time order updates
- `performance` - Performance metric updates
- `webhooks` - Webhook trigger notifications

## SDK Examples

### Python Example

```python
import requests

class TradingAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }

    def get_subscription_plans(self):
        response = requests.get(
            f'{self.base_url}/subscription-plans/',
            headers=self.headers
        )
        return response.json()

    def create_webhook(self, pair_config_id, name):
        data = {
            'pair_config_id': pair_config_id,
            'webhook_name': name
        }
        response = requests.post(
            f'{self.base_url}/custom-bot/webhook/generate/',
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
api = TradingAPI('https://yourdomain.com/api', 'YOUR_TOKEN')
plans = api.get_subscription_plans()
webhook = api.create_webhook(5, 'My Strategy')
```

### JavaScript Example

```javascript
class TradingAPI {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json'
        };
    }

    async getManagedBots() {
        const response = await fetch(`${this.baseUrl}/managed-bot/available/`, {
            headers: this.headers
        });
        return response.json();
    }

    async subscribeToBot(botId, investment) {
        const response = await fetch(`${this.baseUrl}/managed-bot/subscribe/`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                managed_bot_id: botId,
                initial_investment: investment.toString()
            })
        });
        return response.json();
    }
}

// Usage
const api = new TradingAPI('https://yourdomain.com/api', 'YOUR_TOKEN');
api.getManagedBots().then(bots => console.log(bots));
```

## Testing and Development

### Test Environment

- **Base URL**: `https://test-api.yourdomain.com/api`
- **Webhook URLs**: `https://test-webhook.yourdomain.com/...`
- **Demo Trading**: All trading endpoints default to demo mode

### Test Credentials

For testing purposes, you can use demo exchange credentials:
- **Binance Testnet**: API keys available at https://testnet.binance.vision
- **Bybit Testnet**: API keys available at https://testnet.bybit.com

## Support

- **Documentation**: https://docs.yourdomain.com
- **API Status**: https://status.yourdomain.com
- **Support Email**: api-support@yourdomain.com
- **GitHub Issues**: https://github.com/your-org/crypto-trading-platform/issues

## Changelog

### v1.0.0 (2025-01-01)
- Initial API release
- Subscription management
- Custom bot webhooks
- Managed bot services
- TradingView integration

---

**Note**: This API is under active development. Endpoints and features may be added or modified. Check the changelog for updates.