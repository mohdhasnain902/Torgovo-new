# Torgovo-new
creating a Trading bot website backend


PROJECT CONTEXT:
- Django crypto trading bot platform
- Repository: github.com/MuhammadUlHasnain/Torgovo
- Existing models: User, PairConfig, Order, Indicator
- Users already have exchange API credentials (API, SECRET, Demo fields)

TASK: Create Subscription System Backend ONLY (No Frontend Code)

REQUIREMENTS:

1. CREATE NEW MODELS in existing app:

A. SubscriptionPlan Model:
   - plan_type: CHOICE ['custom_bot', 'managed_bot']
   - name: CharField (e.g., "Custom Bot Basic", "Managed Bot Premium")
   - monthly_price: DecimalField
   - description: TextField
   - features: JSONField (for flexible feature list)
   - guaranteed_monthly_return: DecimalField (for managed bots, e.g., 2-15%)
   - profit_share_percentage: DecimalField (for managed bots, e.g., 20-50%)
   - max_trading_pairs: IntegerField (for custom bots)
   - is_active: BooleanField

B. UserSubscription Model:
   - user: ForeignKey to User model
   - plan: ForeignKey to SubscriptionPlan
   - status: CHOICE ['active', 'cancelled', 'expired', 'trial']
   - start_date: DateTimeField
   - end_date: DateTimeField
   - auto_renew: BooleanField
   - payment_method: CharField (for future: 'stripe', 'crypto', etc.)
   
C. CustomBotWebhook Model:
   - user: ForeignKey to User
   - subscription: ForeignKey to UserSubscription
   - webhook_url: CharField (auto-generated unique URL)
   - webhook_secret: CharField (for security validation)
   - tradingview_config: JSONField (stores the JSON payload format)
   - pair_config: ForeignKey to PairConfig
   - is_active: BooleanField
   - created_at: DateTimeField

D. ManagedBotPerformance Model:
   - user: ForeignKey to User
   - subscription: ForeignKey to UserSubscription
   - managed_bot: ForeignKey to PairConfig (the bot they're subscribed to)
   - initial_investment: DecimalField
   - current_balance: DecimalField
   - total_profit: DecimalField
   - total_loss: DecimalField
   - profit_share_paid: DecimalField
   - last_calculated: DateTimeField

2. CREATE API ENDPOINTS (Django REST Framework):

/api/subscription-plans/
   - GET: List all active subscription plans (with filtering by plan_type)

/api/subscriptions/
   - POST: Create new subscription (user subscribes to a plan)
   - GET: Get user's active subscriptions

/api/subscriptions/{id}/
   - GET: Subscription details
   - PATCH: Update subscription (cancel, change auto_renew)
   - DELETE: Cancel subscription

/api/subscriptions/my-subscription/
   - GET: Current user's subscription with plan details

/api/custom-bot/webhook/generate/
   - POST: Generate webhook URL and TradingView JSON config for user

/api/custom-bot/webhook/receive/{webhook_secret}/
   - POST: Receive TradingView webhook alerts and execute trades
   - Should validate webhook_secret
   - Parse JSON payload and trigger bot orders

/api/managed-bot/available/
   - GET: List available managed bots with performance stats

/api/managed-bot/subscribe/
   - POST: Subscribe to a managed bot with investment amount

/api/managed-bot/performance/
   - GET: User's managed bot performance and profit/loss

3. INTEGRATE WITH EXISTING SYSTEM:
   - UserSubscription should check if user has active subscription before allowing bot creation
   - Webhook endpoint should use existing TradingManager to execute trades
   - Add middleware/decorator to check subscription status on protected endpoints

4. WEBHOOK SECURITY:
   - Validate incoming TradingView webhooks using webhook_secret
   - Rate limiting on webhook endpoint
   - Log all webhook requests for debugging

5. PROFIT CALCULATION LOGIC (for managed bots):
   - Calculate profit/loss from Order model
   - Apply profit_share_percentage only on profits
   - Create utility function to calculate and update ManagedBotPerformance

DELIVERABLES:
- models.py (new models added to existing file)
- serializers.py
- views.py (ViewSets/APIViews)
- urls.py
- utils.py (helper functions for webhook generation, profit calculation)
- API_DOCUMENTATION.md with:
  * All endpoints
  * Request/response JSON examples
  * TradingView webhook JSON format
  * Authentication requirements

CONSTRAINTS:
- DO NOT create any React/frontend code
- Use existing User model (don't create new user model)
- Integrate with existing TradingManager class
- Follow Django REST Framework best practices
- Use timezone-aware datetime (Asia/Karachi as in existing code)

EXAMPLE WEBHOOK JSON FORMAT TO GENERATE:
{
  "webhook_url": "https://yourdomain.com/api/custom-bot/webhook/receive/abc123xyz/",
  "tradingview_json": {
    "action": "{{strategy.order.action}}",
    "ticker": "{{ticker}}",
    "price": "{{close}}",
    "quantity": "{{strategy.order.contracts}}",
    "secret": "abc123xyz"
  }
}
```

---

## **PROMPT 2: Payment Integration (Phase 2)**
```
PROJECT CONTEXT:
- Existing subscription system created in previous step
- Need payment gateway integration

TASK: Add Payment Gateway to Subscription System (Backend Only)

REQUIREMENTS:
1. Choose payment gateway: [SPECIFY: Stripe, PayPal, or crypto payment]
2. Create Payment model to track transactions
3. Add payment endpoints:
   - POST /api/payments/create-checkout/
   - POST /api/payments/webhook/ (for payment confirmation)
   - GET /api/payments/history/

4. Update UserSubscription to activate only after successful payment
5. Add recurring billing for monthly subscriptions

DELIVERABLES:
- Payment model and serializer
- Payment views and URLs
- Webhook handler for payment gateway
- Environment variable configuration for API keys
- Updated API documentation

CONSTRAINTS:
- Backend only
- Secure API key handling
- Proper error handling for failed payments
```

---

## **PROMPT 3: Generate API Documentation**
```
TASK: Generate Complete API Documentation

Based on the subscription system and webhook endpoints created, provide a comprehensive API_DOCUMENTATION.md file with:

1. Authentication (existing token-based auth)
2. All new subscription endpoints with:
   - HTTP method and URL
   - Required headers
   - Request body (JSON example)
   - Success response (JSON example)
   - Error responses
   
3. TradingView Webhook Integration Guide:
   - How to generate webhook URL
   - TradingView alert JSON format
   - How webhook triggers bot trades
   
4. Managed Bot Subscription Flow:
   - How to subscribe with investment
   - Profit calculation methodology
   - Profit-sharing examples

FORMAT: Clear markdown with curl examples for each endpoint

This documentation will be used by frontend developer to build React interface.
```

---

## **ADDITIONAL INFORMATION **

### **Key Integration Points:**
```
- Webhook should call: trading_manager.create_bot() and trading_manager.start_bot()
- Use existing PairConfig model for bot configuration
- Orders should be saved to existing Order model
- User's exchange credentials (API, SECRET) from User model
