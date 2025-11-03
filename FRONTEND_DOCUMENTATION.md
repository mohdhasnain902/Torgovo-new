# Frontend Development Documentation

## Overview

This document provides complete specifications for building the frontend for the Crypto Trading Platform backend system. It includes all API endpoints, data structures, authentication flow, and implementation details needed to create a fully functional React/Vue.js frontend.

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [API Base Configuration](#api-base-configuration)
3. [User Management](#user-management)
4. [Subscription System](#subscription-system)
5. [Custom Trading Bots](#custom-trading-bots)
6. [Managed Bot Services](#managed-bot-services)
7. [TradingView Integration](#tradingview-integration)
8. [Dashboard & Analytics](#dashboard--analytics)
9. [Data Models & Types](#data-models--types)
10. [UI Components Guide](#ui-components-guide)
11. [Error Handling](#error-handling)
12. [Real-time Updates](#real-time-updates)

## Authentication Flow

### 1. User Registration

**Endpoint**: `POST /api/users/register/`

**Request Format**:
```typescript
interface RegistrationRequest {
  username: string;           // Required, unique
  email: string;             // Required, unique, valid email
  first_name: string;        // Optional
  last_name: string;         // Optional
  password: string;          // Required, min 8 characters
  password_confirm: string;  // Required, must match password
}
```

**Response Format**:
```typescript
interface RegistrationResponse {
  user: {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    full_name: string;
    date_joined: string;
  };
  token: string;             // JWT token for API calls
  message: string;
}
```

**Implementation Example**:
```javascript
const registerUser = async (userData: RegistrationRequest) => {
  try {
    const response = await fetch('/api/users/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });

    const data = await response.json();

    if (response.ok) {
      localStorage.setItem('authToken', data.token);
      return data;
    } else {
      throw new Error(data.error?.message || 'Registration failed');
    }
  } catch (error) {
    throw error;
  }
};
```

### 2. User Login

**Endpoint**: `POST /api/users/login/`

**Request Format**:
```typescript
interface LoginRequest {
  username: string;
  password: string;
}
```

**Response Format**:
```typescript
interface LoginResponse {
  user: {
    id: number;
    username: string;
    email: string;
    full_name: string;
  };
  token: string;
  message: string;
}
```

### 3. Authentication Headers

All authenticated requests must include:
```javascript
const headers = {
  'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
  'Content-Type': 'application/json',
};
```

## API Base Configuration

### Base URL Configuration
```javascript
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://yourdomain.com/api'
  : 'http://localhost:8000/api';
```

### Axios Configuration Example
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

## User Management

### 1. Get User Profile

**Endpoint**: `GET /api/users/profile/`

**Response Format**:
```typescript
interface UserProfile {
  id: number;
  user: {
    id: number;
    username: string;
    email: string;
  };
  exchange: 'binance' | 'bybit' | 'kraken' | 'mexc';
  exchange_display: string;
  api_key: string;        // Write-only for updates
  api_secret: string;     // Write-only for updates
  demo_mode: boolean;
  timezone: string;
  leverage: number;
  max_position_size: string;
  email_notifications: boolean;
  trade_notifications: boolean;
  profit_loss_notifications: boolean;
  max_daily_loss: string;
  stop_loss_percentage: string;
  take_profit_percentage: string;
  created_at: string;
  updated_at: string;
  is_active_trader: boolean;
  total_traded_volume: string;
  profit_loss_summary: {
    total_buy_value: string;
    total_sell_value: string;
    gross_profit: string;
    total_orders: number;
    buy_orders: number;
    sell_orders: number;
  };
}
```

### 2. Update User Profile

**Endpoint**: `PUT /api/users/profile/`

**Request Format**:
```typescript
interface ProfileUpdateRequest {
  exchange?: 'binance' | 'bybit' | 'kraken' | 'mexc';
  api_key?: string;        // Only for updating credentials
  api_secret?: string;     // Only for updating credentials
  demo_mode?: boolean;
  timezone?: string;
  leverage?: number;       // 1-100
  max_position_size?: string;
  email_notifications?: boolean;
  trade_notifications?: boolean;
  max_daily_loss?: string;
  stop_loss_percentage?: string;  // 0-50
  take_profit_percentage?: string; // 0-100
}
```

### 3. Get User Statistics

**Endpoint**: `GET /api/users/statistics/`

**Response Format**:
```typescript
interface UserStatistics {
  total_traded_volume: string;
  total_orders: number;
  active_subscriptions: number;
  is_active_trader: boolean;
  profit_loss_summary: {
    total_buy_value: string;
    total_sell_value: string;
    gross_profit: string;
    total_orders: number;
    buy_orders: number;
    sell_orders: number;
  };
}
```

## Subscription System

### 1. Get Subscription Plans

**Endpoint**: `GET /api/subscription-plans/`

**Query Parameters**:
- `plan_type` (optional): 'custom_bot' | 'managed_bot'

**Response Format**:
```typescript
interface SubscriptionPlan {
  id: number;
  plan_type: 'custom_bot' | 'managed_bot';
  plan_type_display: string;
  name: string;
  description: string;
  features: {
    [key: string]: any;
  };
  monthly_price: string;
  yearly_price?: string;
  setup_fee: string;
  max_trading_pairs?: number;  // Custom bot specific
  max_bots?: number;          // Custom bot specific
  guaranteed_monthly_return?: string;  // Managed bot specific
  profit_share_percentage?: string;    // Managed bot specific
  min_investment?: string;            // Managed bot specific
  api_calls_per_day: number;
  webhook_requests_per_hour: number;
  concurrent_bots: number;
  is_active: boolean;
  is_public: boolean;
  is_featured: boolean;
  subscriber_count: number;
  created_at: string;
}
```

### 2. Create Subscription

**Endpoint**: `POST /api/subscriptions/`

**Request Format**:
```typescript
interface CreateSubscriptionRequest {
  plan_id: number;
  billing_cycle: 'monthly' | 'yearly';
  auto_renew: boolean;
  payment_method?: string;
}
```

**Response Format**:
```typescript
interface Subscription {
  id: number;
  user: {
    id: number;
    username: string;
  };
  plan: {
    id: number;
    name: string;
    plan_type: 'custom_bot' | 'managed_bot';
  };
  status: 'trial' | 'active' | 'cancelled' | 'expired' | 'suspended';
  status_display: string;
  billing_cycle: 'monthly' | 'yearly';
  start_date: string;
  end_date: string;
  trial_end_date?: string;
  auto_renew: boolean;
  is_active_trial: boolean;
  is_currently_active: boolean;
  days_remaining: number;
  usage_stats: {
    api_calls_used: number;
    api_calls_limit: number;
    api_calls_remaining: number;
    webhook_requests_used: number;
    webhook_requests_limit: number;
    webhook_requests_remaining: number;
  };
  created_at: string;
}
```

### 3. Get My Subscription

**Endpoint**: `GET /api/subscriptions/my-subscription/`

**Response Format**: Same as above Subscription interface

### 4. Get Subscription Usage

**Endpoint**: `GET /api/subscriptions/usage/`

**Response Format**:
```typescript
interface SubscriptionUsage {
  api_calls_used: number;
  api_calls_limit: number;
  api_calls_remaining: number;
  webhook_requests_used: number;
  webhook_requests_limit: number;
  webhook_requests_remaining: number;
  bots_used: number;
  bots_limit: number;
  pairs_used: number;
  pairs_limit: number;
}
```

## Custom Trading Bots

### 1. Create Webhook

**Endpoint**: `POST /api/custom-bot/webhook/generate/`

**Request Format**:
```typescript
interface CreateWebhookRequest {
  pair_config_id: number;
  webhook_name: string;
  allow_ip_whitelist?: boolean;
  allowed_ips?: string[];
  require_signature?: boolean;
}
```

**Response Format**:
```typescript
interface CustomBotWebhook {
  id: number;
  user: {
    id: number;
    username: string;
  };
  subscription: {
    id: number;
    plan: {
      name: string;
    };
  };
  pair_config: {
    id: number;
    name: string;
    pair_symbol: string;
    exchange: string;
    exchange_display: string;
  };
  webhook_name: string;
  webhook_url: string;
  webhook_secret: string;
  tradingview_config: {
    webhook_url: string;
    tradingview_json: {
      action: string;
      ticker: string;
      price: string;
      quantity: string;
      secret: string;
    };
  };
  is_active: boolean;
  total_triggers: number;
  successful_triggers: number;
  success_rate: number;
  created_at: string;
}
```

### 2. Get Webhooks List

**Endpoint**: `GET /api/custom-bot/webhook/`

**Response Format**: Array of CustomBotWebhook

### 3. Update Webhook

**Endpoint**: `PATCH /api/custom-bot/webhook/{id}/`

**Request Format**:
```typescript
interface UpdateWebhookRequest {
  webhook_name?: string;
  is_active?: boolean;
  allow_ip_whitelist?: boolean;
  allowed_ips?: string[];
  require_signature?: boolean;
}
```

### 4. Test Webhook

**Endpoint**: `GET /api/custom-bot/webhook/test/{webhook_secret}/`

**Response Format**:
```typescript
interface WebhookTestResponse {
  status: 'success' | 'error';
  webhook: {
    id: number;
    name: string;
    pair_config: {
      symbol: string;
      exchange: string;
    };
    is_active: boolean;
    total_triggers: number;
    successful_triggers: number;
    last_triggered: string;
  };
}
```

## Managed Bot Services

### 1. Get Available Managed Bots

**Endpoint**: `GET /api/managed-bot/available/`

**Query Parameters**:
- `exchange` (optional): Filter by exchange
- `pair` (optional): Filter by trading pair
- `strategy` (optional): Filter by strategy type

**Response Format**:
```typescript
interface AvailableManagedBot {
  id: number;
  name: string;
  pair_symbol: string;
  exchange: string;
  strategy_type: string;
  description: string;
  performance_30d: string;  // Percentage string
  performance_90d: string;  // Percentage string
  total_subscribers: number;
  min_investment: string;
  profit_share_percentage: string;
  guaranteed_monthly_return: string;
}
```

### 2. Subscribe to Managed Bot

**Endpoint**: `POST /api/managed-bot/subscribe/`

**Request Format**:
```typescript
interface ManagedBotSubscriptionRequest {
  managed_bot_id: number;
  initial_investment: string;
}
```

**Response Format**:
```typescript
interface ManagedBotSubscription {
  performance: {
    id: number;
    user: {
      id: number;
      username: string;
    };
    subscription: {
      id: number;
      plan: {
        name: string;
      };
    };
    managed_bot: {
      id: number;
      name: string;
      pair_symbol: string;
      exchange: string;
    };
    initial_investment: string;
    current_balance: string;
    net_return: string;
    net_return_percentage: string;
    profit_share_remaining: string;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: string;
    created_at: string;
  };
  session_id: string;
  message: string;
}
```

### 3. Get Managed Bot Performance

**Endpoint**: `GET /api/managed-bot/performance/`

**Query Parameters**:
- `period_days` (optional): Number of days (default: 30)
- `bot_id` (optional): Specific bot ID

**Response Format**:
```typescript
interface ManagedBotPerformanceResponse {
  summary: {
    period_days: number;
    total_invested: string;
    current_value: string;
    total_profit: string;
    total_loss: string;
    net_profit: string;
    profit_percentage: string;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: string;
    bot_breakdown: Array<{
      bot_name: string;
      initial_investment: string;
      current_balance: string;
      net_profit: string;
      profit_percentage: string;
    }>;
  };
  bots: Array<{
    id: number;
    managed_bot: {
      id: number;
      name: string;
      pair_symbol: string;
      exchange: string;
    };
    initial_investment: string;
    current_balance: string;
    total_profit: string;
    total_loss: string;
    net_profit: string;
    profit_percentage: string;
    net_return: string;
    net_return_percentage: string;
    profit_share_paid: string;
    profit_share_remaining: string;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    win_rate: string;
  }>;
  period_days: number;
}
```

### 4. Get Managed Bot Rankings

**Endpoint**: `GET /api/managed-bot/rankings/`

**Query Parameters**:
- `period_days` (optional): Ranking period in days (default: 30)

**Response Format**:
```typescript
interface ManagedBotRankings {
  period_days: number;
  rankings: Array<{
    bot_id: number;
    bot_name: string;
    pair_symbol: string;
    exchange: string;
    strategy_type: string;
    total_subscribers: number;
    total_invested: string;
    avg_performance: string;
    total_trades: number;
  }>;
}
```

## TradingView Integration

### TradingView Webhook Setup

**Generated TradingView Configuration**:
```json
{
  "webhook_url": "https://yourdomain.com/api/custom-bot/webhook/receive/{webhook_secret}/",
  "tradingview_json": {
    "action": "{{strategy.order.action}}",
    "ticker": "{{ticker}}",
    "price": "{{close}}",
    "quantity": "{{strategy.order.contracts}}",
    "secret": "{webhook_secret}"
  }
}
```

### TradingView Alert Configuration

1. **Create Strategy** in TradingView Pine Editor
2. **Add Alert** with these settings:
   - **Condition**: Your strategy entry/exit signals
   - **Action**: Webhook URL
   - **Webhook URL**: Use the generated webhook_url
   - **Message**: Use the tradingview_json template

### Supported TradingView Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{strategy.order.action}}` | Buy/Sell action | "buy" or "sell" |
| `{{ticker}}` | Trading pair symbol | "BTCUSDT" |
| `{{close}}` | Current price | "45000.50" |
| `{{strategy.order.contracts}}` | Order quantity | "0.01" |
| `{{time}}` | Timestamp | "2025-01-01T10:30:00Z" |

## Dashboard & Analytics

### 1. Dashboard Data Aggregation

**Combine multiple API calls for comprehensive dashboard**:

```typescript
interface DashboardData {
  userProfile: UserProfile;
  subscription: Subscription | null;
  usage: SubscriptionUsage;
  statistics: UserStatistics;
  activeWebhooks: CustomBotWebhook[];
  managedBotPerformance: ManagedBotPerformanceResponse | null;
  recentOrders: Order[]; // From trading/orders/ endpoint
}
```

### 2. Performance Charts Data

**For charting libraries (Chart.js, D3.js, etc.)**:

```typescript
interface ChartData {
  labels: string[];          // Time periods
  datasets: {
    label: string;
    data: number[];
    borderColor: string;
    backgroundColor: string;
    fill?: boolean;
  }[];
}

// Example: Portfolio performance over time
const portfolioPerformanceData: ChartData = {
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
  datasets: [{
    label: 'Portfolio Value',
    data: [10000, 10500, 11200, 10800, 11500, 12300],
    borderColor: '#4CAF50',
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
    fill: true,
  }]
};
```

### 3. Real-time Updates

**WebSocket Connection** (when implemented):
```javascript
const ws = new WebSocket('wss://yourdomain.com/ws/updates/');

ws.onopen = () => {
  console.log('Connected to real-time updates');
  ws.send(JSON.stringify({
    channel: 'orders',
    auth_token: localStorage.getItem('authToken')
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleRealtimeUpdate(data);
};
```

## Data Models & Types

### Complete TypeScript Definitions

```typescript
// Enums
type Exchange = 'binance' | 'bybit' | 'kraken' | 'mexc';
type PlanType = 'custom_bot' | 'managed_bot';
type SubscriptionStatus = 'trial' | 'active' | 'cancelled' | 'expired' | 'suspended';
type OrderAction = 'buy' | 'sell';
type OrderType = 'market' | 'limit' | 'stop_loss' | 'take_profit';

// Base Models
interface BaseModel {
  id: number;
  created_at: string;
  updated_at?: string;
}

// User Models
interface User extends BaseModel {
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  date_joined: string;
}

// Subscription Models
interface Plan extends BaseModel {
  plan_type: PlanType;
  name: string;
  description: string;
  features: Record<string, any>;
  monthly_price: string;
  yearly_price?: string;
  setup_fee: string;
  is_active: boolean;
  is_public: boolean;
  subscriber_count: number;
}

// Trading Models
interface PairConfig extends BaseModel {
  name: string;
  pair_symbol: string;
  exchange: Exchange;
  min_order_size: string;
  max_order_size: string;
  is_managed: boolean;
  guaranteed_monthly_return?: string;
  profit_share_percentage?: string;
  min_investment?: string;
}

interface Order extends BaseModel {
  user: number;
  pair_config: PairConfig;
  action: OrderAction;
  order_type: OrderType;
  quantity: string;
  price: string;
  executed_price?: string;
  executed_quantity?: string;
  status: 'pending' | 'executed' | 'cancelled' | 'failed';
  total_value: string;
  profit_loss: string;
}

// Webhook Models
interface Webhook extends BaseModel {
  user: User;
  subscription: Subscription;
  pair_config: PairConfig;
  webhook_name: string;
  webhook_url: string;
  webhook_secret: string;
  is_active: boolean;
  total_triggers: number;
  successful_triggers: number;
  success_rate: number;
  tradingview_config: TradingViewConfig;
}

interface TradingViewConfig {
  webhook_url: string;
  tradingview_json: {
    action: string;
    ticker: string;
    price: string;
    quantity: string;
    secret: string;
  };
}
```

## UI Components Guide

### 1. Authentication Components

**LoginForm Component**:
```typescript
interface LoginFormProps {
  onSubmit: (credentials: LoginRequest) => Promise<void>;
  loading?: boolean;
  error?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSubmit, loading, error }) => {
  const [formData, setFormData] = useState<LoginRequest>({
    username: '',
    password: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await onSubmit(formData);
    } catch (error) {
      // Handle error
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Username"
        value={formData.username}
        onChange={(e) => setFormData({...formData, username: e.target.value})}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={formData.password}
        onChange={(e) => setFormData({...formData, password: e.target.value})}
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </button>
      {error && <div className="error">{error}</div>}
    </form>
  );
};
```

### 2. Subscription Components

**SubscriptionPlanCard Component**:
```typescript
interface SubscriptionPlanCardProps {
  plan: Plan;
  onSubscribe: (planId: number) => void;
  currentSubscription?: Subscription;
}

const SubscriptionPlanCard: React.FC<SubscriptionPlanCardProps> = ({
  plan,
  onSubscribe,
  currentSubscription
}) => {
  const isSubscribed = currentSubscription?.plan.id === plan.id;

  return (
    <div className={`plan-card ${plan.is_featured ? 'featured' : ''}`}>
      <h3>{plan.name}</h3>
      <div className="price">
        ${plan.monthly_price}/month
        {plan.yearly_price && (
          <span className="yearly">
            ${plan.yearly_price}/year
            <small>Save {plan.yearly_savings_percentage}%</small>
          </span>
        )}
      </div>

      <div className="features">
        {Object.entries(plan.features).map(([key, value]) => (
          <div key={key} className="feature">
            {typeof value === 'boolean' ? (
              <span className={value ? 'included' : 'not-included'}>
                {value ? '✓' : '✗'}
              </span>
            ) : (
              <span>{value}</span>
            )}
            <span>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
          </div>
        ))}
      </div>

      <button
        onClick={() => onSubscribe(plan.id)}
        disabled={isSubscribed}
        className={isSubscribed ? 'subscribed' : 'subscribe'}
      >
        {isSubscribed ? 'Current Plan' : 'Subscribe'}
      </button>
    </div>
  );
};
```

### 3. Dashboard Components

**UsageProgress Component**:
```typescript
interface UsageProgressProps {
  used: number;
  limit: number;
  label: string;
  color?: string;
}

const UsageProgress: React.FC<UsageProgressProps> = ({
  used,
  limit,
  label,
  color = '#4CAF50'
}) => {
  const percentage = (used / limit) * 100;
  const isNearLimit = percentage > 80;

  return (
    <div className="usage-progress">
      <div className="usage-header">
        <span>{label}</span>
        <span>{used} / {limit}</span>
      </div>
      <div className="progress-bar">
        <div
          className={`progress-fill ${isNearLimit ? 'warning' : ''}`}
          style={{
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: color
          }}
        />
      </div>
    </div>
  );
};
```

**PerformanceChart Component**:
```typescript
interface PerformanceChartProps {
  data: ChartData;
  title: string;
  type?: 'line' | 'bar';
}

const PerformanceChart: React.FC<PerformanceChartProps> = ({
  data,
  title,
  type = 'line'
}) => {
  const chartRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (chartRef.current) {
      const ctx = chartRef.current.getContext('2d');
      // Initialize Chart.js or your preferred charting library
      new Chart(ctx, {
        type,
        data,
        options: {
          responsive: true,
          plugins: {
            legend: {
              position: 'top',
            },
            title: {
              display: true,
              text: title
            }
          }
        }
      });
    }
  }, [data, title, type]);

  return <canvas ref={chartRef} />;
};
```

### 4. Webhook Components

**WebhookStatus Component**:
```typescript
interface WebhookStatusProps {
  webhook: Webhook;
}

const WebhookStatus: React.FC<WebhookStatusProps> = ({ webhook }) => {
  return (
    <div className="webhook-status">
      <div className="status-header">
        <h4>{webhook.webhook_name}</h4>
        <div className={`status-indicator ${webhook.is_active ? 'active' : 'inactive'}`}>
          {webhook.is_active ? 'Active' : 'Inactive'}
        </div>
      </div>

      <div className="trading-pair">
        <span>{webhook.pair_config.pair_symbol}</span>
        <span className="exchange">{webhook.pair_config.exchange.toUpperCase()}</span>
      </div>

      <div className="statistics">
        <div className="stat">
          <span className="label">Total Triggers:</span>
          <span className="value">{webhook.total_triggers}</span>
        </div>
        <div className="stat">
          <span className="label">Success Rate:</span>
          <span className="value">{webhook.success_rate}%</span>
        </div>
        <div className="stat">
          <span className="label">Last Triggered:</span>
          <span className="value">
            {webhook.last_triggered
              ? new Date(webhook.last_triggered).toLocaleString()
              : 'Never'
            }
          </span>
        </div>
      </div>

      <div className="webhook-url">
        <label>Webhook URL:</label>
        <code>{webhook.webhook_url}</code>
        <button onClick={() => navigator.clipboard.writeText(webhook.webhook_url)}>
          Copy
        </button>
      </div>
    </div>
  );
};
```

## Error Handling

### Error Response Format

All API errors follow this structure:
```typescript
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: {
      [key: string]: any;
    };
  };
}
```

### Error Handling Implementation

```typescript
class ApiError extends Error {
  code: string;
  details?: any;

  constructor(message: string, code: string, details?: any) {
    super(message);
    this.code = code;
    this.details = details;
  }
}

const handleApiError = (error: any) => {
  if (error.response) {
    const { status, data } = error.response;

    switch (status) {
      case 400:
        throw new ApiError(data.error?.message || 'Bad Request', 'VALIDATION_ERROR', data.error?.details);
      case 401:
        throw new ApiError('Authentication required', 'AUTHENTICATION_ERROR');
      case 403:
        throw new ApiError('Insufficient permissions', 'PERMISSION_ERROR');
      case 404:
        throw new ApiError('Resource not found', 'NOT_FOUND_ERROR');
      case 429:
        throw new ApiError('Rate limit exceeded', 'RATE_LIMIT_ERROR');
      case 500:
        throw new ApiError('Server error', 'SERVER_ERROR');
      default:
        throw new ApiError('Unknown error occurred', 'UNKNOWN_ERROR');
    }
  } else if (error.request) {
    throw new ApiError('Network error', 'NETWORK_ERROR');
  } else {
    throw new ApiError(error.message, 'UNKNOWN_ERROR');
  }
};
```

### Error Boundary Component

```typescript
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <details>
            {this.state.error?.message}
          </details>
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## Real-time Updates

### WebSocket Channels

When WebSocket support is added, these channels will be available:

#### 1. Order Updates Channel
```typescript
interface OrderUpdateMessage {
  channel: 'orders';
  type: 'created' | 'updated' | 'executed';
  data: Order;
}
```

#### 2. Performance Updates Channel
```typescript
interface PerformanceUpdateMessage {
  channel: 'performance';
  type: 'profit_loss' | 'trade_executed';
  data: {
    bot_id: number;
    new_profit_loss: string;
    current_balance: string;
  };
}
```

#### 3. Webhook Status Channel
```typescript
interface WebhookStatusMessage {
  channel: 'webhooks';
  type: 'triggered' | 'error';
  data: {
    webhook_id: number;
    status: string;
    timestamp: string;
  };
}
```

### Real-time Hook Example

```typescript
const useRealTimeUpdates = (channels: string[]) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (!token) return;

    const ws = new WebSocket(`wss://yourdomain.com/ws/updates/?token=${token}`);

    ws.onopen = () => {
      setIsConnected(true);
      channels.forEach(channel => {
        ws.send(JSON.stringify({ action: 'subscribe', channel }));
      });
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      // Handle real-time updates
      handleRealtimeMessage(message);
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [channels]);

  return { socket, isConnected };
};
```

## Deployment Considerations

### Environment Variables
```javascript
const config = {
  apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  wsUrl: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  enableRealtime: process.env.REACT_APP_ENABLE_REALTIME === 'true',
  debugMode: process.env.NODE_ENV === 'development',
};
```

### Build Configuration
```javascript
// package.json
{
  "scripts": {
    "build": "REACT_APP_API_URL=https://yourdomain.com/api react-scripts build",
    "build:dev": "REACT_APP_API_URL=http://localhost:8000/api react-scripts build"
  }
}
```

### Security Headers
```javascript
// Ensure secure headers in production
if (process.env.NODE_ENV === 'production') {
  // Set secure cookie attributes
  document.cookie = `authToken=${token}; Secure; HttpOnly; SameSite=Strict`;
}
```

## Final Implementation Checklist

- [ ] Authentication flow (login, register, token management)
- [ ] User profile management with exchange credentials
- [ ] Subscription plan display and management
- [ ] Usage monitoring and limits display
- [ ] Custom bot webhook creation and management
- [ ] TradingView integration setup guide
- [ ] Managed bot subscription and performance tracking
- [ ] Real-time dashboard with charts and analytics
- [ ] Error handling and user feedback
- [ ] Responsive design for mobile devices
- [ ] Loading states and skeleton screens
- [ ] Form validation and user input sanitization
- [ ] Secure storage of authentication tokens
- [ ] API rate limiting handling
- [ ] Offline support considerations

This comprehensive documentation provides everything needed to build a complete frontend for the crypto trading platform backend system.