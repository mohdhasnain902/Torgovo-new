"""
Utility functions for subscriptions app.
"""
import secrets
import string
import time
import logging
from decimal import Decimal
from datetime import timedelta, datetime
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import (
    CustomBotWebhook, UserSubscription, ManagedBotPerformance,
    SubscriptionPlan
)

# Configure logging
webhook_logger = logging.getLogger('webhooks')
performance_logger = logging.getLogger('performance')


def generate_webhook_secret(length=32):
    """
    Generate a secure webhook secret using the secrets module.

    Args:
        length: Length of the secret (default: 32)

    Returns:
        str: Secure random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_webhook_url(webhook_secret):
    """
    Generate webhook URL for the given secret.

    Args:
        webhook_secret: Webhook secret string

    Returns:
        str: Complete webhook URL
    """
    base_url = getattr(settings, 'BASE_URL', 'https://yourdomain.com')
    return f"{base_url}/api/custom-bot/webhook/receive/{webhook_secret}/"


def generate_tradingview_config(webhook_secret):
    """
    Generate TradingView configuration JSON for webhook.

    Args:
        webhook_secret: Webhook secret string

    Returns:
        dict: TradingView configuration
    """
    return {
        "action": "{{strategy.order.action}}",
        "ticker": "{{ticker}}",
        "price": "{{close}}",
        "quantity": "{{strategy.order.contracts}}",
        "secret": webhook_secret
    }


def validate_webhook_request(request, webhook_secret):
    """
    Validate incoming webhook request.

    Args:
        request: Django request object
        webhook_secret: Webhook secret to validate

    Returns:
        tuple: (is_valid, webhook_instance, error_message)
    """
    try:
        # Get webhook instance
        webhook = CustomBotWebhook.objects.select_related('user', 'subscription').get(
            webhook_secret=webhook_secret
        )
    except CustomBotWebhook.DoesNotExist:
        return False, None, "Invalid webhook secret"

    # Check if webhook is active
    if not webhook.is_active:
        return False, webhook, "Webhook is inactive"

    # Check rate limits
    can_use, message = webhook.check_rate_limit()
    if not can_use:
        return False, webhook, message

    # Check IP whitelist if enabled
    if webhook.allow_ip_whitelist:
        client_ip = get_client_ip(request)
        if client_ip not in webhook.allowed_ips:
            return False, webhook, f"IP address {client_ip} not allowed"

    # Check subscription status
    if not webhook.subscription.is_currently_active:
        return False, webhook, "Subscription not active"

    return True, webhook, None


def get_client_ip(request):
    """
    Get client IP address from request.

    Args:
        request: Django request object

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_webhook_request(request, webhook_secret, response_status, webhook_instance=None):
    """
    Log webhook request for debugging and monitoring.

    Args:
        request: Django request object
        webhook_secret: Webhook secret
        response_status: HTTP response status
        webhook_instance: CustomBotWebhook instance (optional)
    """
    try:
        payload_data = request.data if hasattr(request, 'data') else {}

        # Sanitize sensitive data for logging
        safe_payload = {
            'action': payload_data.get('action'),
            'ticker': payload_data.get('ticker'),
            'price': payload_data.get('price'),
            'quantity': payload_data.get('quantity'),
            'secret': payload_data.get('secret', '')[:4] + '...' if payload_data.get('secret') else None
        }

        log_data = {
            'webhook_secret': webhook_secret,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'payload': safe_payload,
            'response_status': response_status,
            'timestamp': timezone.now().isoformat()
        }

        # Add webhook-specific info if available
        if webhook_instance:
            log_data.update({
                'webhook_name': webhook_instance.webhook_name,
                'user': webhook_instance.user.username,
                'pair_config': webhook_instance.pair_config.pair_symbol
            })

        webhook_logger.info(f"Webhook Request: {log_data}")

    except Exception as e:
        webhook_logger.error(f"Error logging webhook request: {e}")


def calculate_managed_bot_performance(user, pair_config):
    """
    Calculate performance metrics for a user's managed bot subscription.

    Args:
        user: Django User object
        pair_config: PairConfig object

    Returns:
        dict: Performance metrics
    """
    from trading.models import Order

    try:
        # Get all executed orders for this user and pair configuration
        orders = Order.objects.filter(
            user=user,
            pair_config=pair_config,
            status='executed'
        ).order_by('created_at')

        if not orders.exists():
            return {
                'total_profit': Decimal('0'),
                'total_loss': Decimal('0'),
                'net_profit': Decimal('0'),
                'profit_percentage': Decimal('0'),
                'current_balance': Decimal('0'),
                'total_orders': 0
            }

        # Calculate total profit and loss using FIFO matching
        total_profit = Decimal('0')
        total_loss = Decimal('0')
        buy_queue = []  # Queue to track open buy orders

        for order in orders:
            if order.action == 'buy':
                # Add buy order to queue
                buy_queue.append({
                    'price': order.executed_price or order.price,
                    'quantity': order.executed_quantity or order.quantity,
                    'timestamp': order.created_at
                })
            elif order.action == 'sell' and buy_queue:
                # Match sell order with earliest buy order (FIFO)
                sell_quantity = order.executed_quantity or order.quantity
                sell_price = order.executed_price or order.price

                while buy_queue and sell_quantity > 0:
                    buy_order = buy_queue[0]
                    match_quantity = min(buy_order['quantity'], sell_quantity)

                    # Calculate profit/loss for this match
                    profit_loss = (sell_price - buy_order['price']) * match_quantity

                    if profit_loss > 0:
                        total_profit += profit_loss
                    else:
                        total_loss += abs(profit_loss)

                    # Update quantities
                    buy_order['quantity'] -= match_quantity
                    sell_quantity -= match_quantity

                    # Remove buy order if fully matched
                    if buy_order['quantity'] <= 0:
                        buy_queue.pop(0)

        # Get initial investment from performance record
        try:
            performance = ManagedBotPerformance.objects.get(
                user=user,
                managed_bot=pair_config
            )
            initial_investment = performance.initial_investment
        except ManagedBotPerformance.DoesNotExist:
            initial_investment = Decimal('0')

        net_profit = total_profit - total_loss
        current_balance = initial_investment + net_profit

        profit_percentage = Decimal('0')
        if initial_investment > 0:
            profit_percentage = (net_profit / initial_investment) * Decimal('100')

        return {
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': net_profit,
            'profit_percentage': profit_percentage,
            'current_balance': current_balance,
            'total_orders': orders.count()
        }

    except Exception as e:
        performance_logger.error(f"Error calculating performance for user {user.id}, pair {pair_config.id}: {e}")
        return {
            'total_profit': Decimal('0'),
            'total_loss': Decimal('0'),
            'net_profit': Decimal('0'),
            'profit_percentage': Decimal('0'),
            'current_balance': Decimal('0'),
            'total_orders': 0
        }


def calculate_profit_share(user, pair_config):
    """
    Calculate profit share amount owed to platform.

    Args:
        user: Django User object
        pair_config: PairConfig object

    Returns:
        dict: Profit share calculation details
    """
    try:
        # Get performance record
        performance = ManagedBotPerformance.objects.select_related('subscription', 'subscription__plan').get(
            user=user,
            managed_bot=pair_config
        )

        # Get subscription plan details
        subscription = performance.subscription
        profit_share_percentage = subscription.plan.profit_share_percentage or Decimal('0')

        # Calculate profit share only on profits (not losses)
        profit_share_owed = performance.total_profit * (profit_share_percentage / Decimal('100'))
        profit_share_remaining = profit_share_owed - performance.profit_share_paid

        return {
            'profit_share_percentage': profit_share_percentage,
            'total_profit': performance.total_profit,
            'profit_share_owed': profit_share_owed,
            'profit_share_paid': performance.profit_share_paid,
            'profit_share_remaining': profit_share_remaining
        }

    except ManagedBotPerformance.DoesNotExist:
        return {
            'profit_share_percentage': Decimal('0'),
            'total_profit': Decimal('0'),
            'profit_share_owed': Decimal('0'),
            'profit_share_paid': Decimal('0'),
            'profit_share_remaining': Decimal('0')
        }
    except Exception as e:
        performance_logger.error(f"Error calculating profit share for user {user.id}, pair {pair_config.id}: {e}")
        return {
            'profit_share_percentage': Decimal('0'),
            'total_profit': Decimal('0'),
            'profit_share_owed': Decimal('0'),
            'profit_share_paid': Decimal('0'),
            'profit_share_remaining': Decimal('0')
        }


def update_managed_bot_performance(performance, new_order):
    """
    Update ManagedBotPerformance record when new order is executed.

    Args:
        performance: ManagedBotPerformance instance
        new_order: Order instance
    """
    try:
        with transaction.atomic():
            # Lock the performance record to prevent race conditions
            performance = ManagedBotPerformance.objects.select_for_update().get(id=performance.id)

            # Calculate impact of new order
            if new_order.action == 'sell':
                # Find corresponding buy order (simplified FIFO)
                # In production, this would be more sophisticated
                profit_loss = Decimal('0')  # Placeholder - would need proper order matching logic

                if profit_loss > 0:
                    performance.total_profit += profit_loss
                else:
                    performance.total_loss += abs(profit_loss)

                # Update current balance
                performance.current_balance = performance.initial_investment + performance.total_profit - performance.total_loss

                # Update profit share
                profit_share = calculate_profit_share(new_order.user, new_order.pair_config)
                performance.profit_share_owed = profit_share['profit_share_owed']

                # Update total trades
                performance.total_trades += 1

            performance.last_calculated = timezone.now()
            performance.save()

    except Exception as e:
        performance_logger.error(f"Error updating managed bot performance: {e}")


def get_performance_summary(user, period_days=30):
    """
    Get performance summary for a specific time period.

    Args:
        user: Django User object
        period_days: Number of days for the period

    Returns:
        dict: Performance summary
    """
    try:
        end_date = timezone.now()
        start_date = end_date - timedelta(days=period_days)

        # Get user's managed bot performances
        performances = ManagedBotPerformance.objects.filter(user=user)

        summary = {
            'period_days': period_days,
            'total_invested': Decimal('0'),
            'current_value': Decimal('0'),
            'total_profit': Decimal('0'),
            'total_loss': Decimal('0'),
            'net_profit': Decimal('0'),
            'profit_percentage': Decimal('0'),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': Decimal('0'),
            'bot_breakdown': []
        }

        for performance in performances:
            # Add to totals
            summary['total_invested'] += performance.initial_investment
            summary['current_value'] += performance.current_balance
            summary['total_profit'] += performance.total_profit
            summary['total_loss'] += performance.total_loss
            summary['total_trades'] += performance.total_trades
            summary['winning_trades'] += performance.winning_trades
            summary['losing_trades'] += performance.losing_trades

            # Add bot breakdown
            summary['bot_breakdown'].append({
                'bot_name': performance.managed_bot.name,
                'bot_symbol': performance.managed_bot.pair_symbol,
                'initial_investment': performance.initial_investment,
                'current_balance': performance.current_balance,
                'net_profit': performance.net_profit,
                'profit_percentage': performance.profit_percentage,
                'total_trades': performance.total_trades
            })

        # Calculate summary metrics
        summary['net_profit'] = summary['total_profit'] - summary['total_loss']

        if summary['total_invested'] > 0:
            summary['profit_percentage'] = (summary['net_profit'] / summary['total_invested']) * Decimal('100')

        if summary['total_trades'] > 0:
            summary['win_rate'] = (summary['winning_trades'] / summary['total_trades']) * Decimal('100')

        return summary

    except Exception as e:
        performance_logger.error(f"Error getting performance summary for user {user.id}: {e}")
        return {
            'period_days': period_days,
            'total_invested': Decimal('0'),
            'current_value': Decimal('0'),
            'total_profit': Decimal('0'),
            'total_loss': Decimal('0'),
            'net_profit': Decimal('0'),
            'profit_percentage': Decimal('0'),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': Decimal('0'),
            'bot_breakdown': []
        }


def get_managed_bot_rankings(period_days=30):
    """
    Get ranked list of managed bots by performance.

    Args:
        period_days: Number of days to consider for ranking

    Returns:
        list: Ranked list of bots
    """
    try:
        from django.db.models import F, ExpressionWrapper, DecimalField, Avg, Count

        # Get all managed bot performances with profit calculation
        performances = ManagedBotPerformance.objects.annotate(
            profit_percentage = ExpressionWrapper(
                (F('total_profit') - F('total_loss')) * Decimal('100.0') / F('initial_investment'),
                output_field=DecimalField()
            )
        ).filter(
            initial_investment__gt=0,
            total_trades__gt=0  # Only include bots with actual trading activity
        )

        # Group by managed bot and calculate averages
        bot_rankings = {}
        for perf in performances:
            bot_id = perf.managed_bot.id
            if bot_id not in bot_rankings:
                bot_rankings[bot_id] = {
                    'bot_id': bot_id,
                    'bot_name': perf.managed_bot.name,
                    'pair_symbol': perf.managed_bot.pair_symbol,
                    'exchange': perf.managed_bot.exchange,
                    'strategy_type': perf.managed_bot.strategy_type,
                    'total_subscribers': 0,
                    'total_invested': Decimal('0'),
                    'avg_performance': Decimal('0'),
                    'total_trades': 0,
                    'subscribers': []
                }

            bot_rankings[bot_id]['subscribers'].append(perf.profit_percentage)
            bot_rankings[bot_id]['total_subscribers'] += 1
            bot_rankings[bot_id]['total_invested'] += perf.initial_investment
            bot_rankings[bot_id]['total_trades'] += perf.total_trades

        # Calculate averages and sort
        for bot_id, data in bot_rankings.items():
            subscribers = data['subscribers']
            if subscribers:
                data['avg_performance'] = sum(subscribers) / len(subscribers)

        # Sort by average performance
        ranked_bots = sorted(
            bot_rankings.values(),
            key=lambda x: x['avg_performance'],
            reverse=True
        )

        return ranked_bots

    except Exception as e:
        performance_logger.error(f"Error getting managed bot rankings: {e}")
        return []


def check_subscription_limits(user, feature_name):
    """
    Check if user has permission to use a specific feature based on their subscription.

    Args:
        user: Django User object
        feature_name: Feature name to check

    Returns:
        tuple: (has_permission, subscription, message)
    """
    try:
        # Get active subscription
        subscription = UserSubscription.objects.filter(
            user=user,
            status='active',
            end_date__gte=timezone.now()
        ).first()

        if not subscription:
            return False, None, "No active subscription found"

        # Check if feature is included in plan
        if not subscription.can_use_feature(feature_name):
            return False, subscription, f"Feature '{feature_name}' not included in current plan"

        # Check usage limits
        can_use, message = subscription.check_usage_limits()
        if not can_use:
            return False, subscription, message

        return True, subscription, "Permission granted"

    except Exception as e:
        webhook_logger.error(f"Error checking subscription limits for user {user.id}: {e}")
        return False, None, "Error checking subscription limits"


def record_api_usage(user, feature_name):
    """
    Record API usage for a user.

    Args:
        user: Django User object
        feature_name: Feature being used
    """
    try:
        subscription = UserSubscription.objects.filter(
            user=user,
            status='active'
        ).first()

        if subscription:
            subscription.record_api_call()

    except Exception as e:
        webhook_logger.error(f"Error recording API usage for user {user.id}: {e}")


def create_default_subscription_plans():
    """
    Create default subscription plans if they don't exist.
    """
    default_plans = [
        {
            'plan_type': 'custom_bot',
            'name': 'Custom Bot Basic',
            'description': 'Perfect for beginners getting started with automated trading',
            'features': {
                'max_trading_pairs': 3,
                'concurrent_bots': 2,
                'indicators': ['RSI', 'MACD', 'Bollinger Bands'],
                'backtesting': True,
                'basic_analytics': True,
                'email_support': True
            },
            'monthly_price': Decimal('29.99'),
            'max_trading_pairs': 3,
            'max_bots': 2,
            'api_calls_per_day': 1000,
            'webhook_requests_per_hour': 50,
            'concurrent_bots': 2,
            'sort_order': 1
        },
        {
            'plan_type': 'custom_bot',
            'name': 'Custom Bot Pro',
            'description': 'Advanced features for serious traders',
            'features': {
                'max_trading_pairs': 10,
                'concurrent_bots': 5,
                'indicators': ['RSI', 'MACD', 'Bollinger Bands', 'ADX', 'ATR', 'CCI'],
                'backtesting': True,
                'advanced_analytics': True,
                'custom_indicators': True,
                'priority_support': True,
                'paper_trading': True
            },
            'monthly_price': Decimal('99.99'),
            'max_trading_pairs': 10,
            'max_bots': 5,
            'api_calls_per_day': 5000,
            'webhook_requests_per_hour': 200,
            'concurrent_bots': 5,
            'sort_order': 2
        },
        {
            'plan_type': 'managed_bot',
            'name': 'Managed Bot Starter',
            'description': 'Start with professional managed trading with guaranteed returns',
            'features': {
                'guaranteed_returns': True,
                'professional_management': True,
                'daily_reports': True,
                'risk_management': True,
                'email_support': True
            },
            'monthly_price': Decimal('199.99'),
            'guaranteed_monthly_return': Decimal('5.0'),
            'profit_share_percentage': Decimal('25.0'),
            'min_investment': Decimal('1000.00'),
            'api_calls_per_day': 500,
            'webhook_requests_per_hour': 25,
            'concurrent_bots': 1,
            'sort_order': 3
        },
        {
            'plan_type': 'managed_bot',
            'name': 'Managed Bot Premium',
            'description': 'Premium managed trading with higher returns and priority access',
            'features': {
                'guaranteed_returns': True,
                'professional_management': True,
                'daily_reports': True,
                'real_time_alerts': True,
                'risk_management': True,
                'priority_support': True,
                'dedicated_manager': True
            },
            'monthly_price': Decimal('499.99'),
            'guaranteed_monthly_return': Decimal('10.0'),
            'profit_share_percentage': Decimal('30.0'),
            'min_investment': Decimal('5000.00'),
            'api_calls_per_day': 1000,
            'webhook_requests_per_hour': 50,
            'concurrent_bots': 3,
            'sort_order': 4,
            'is_featured': True
        }
    ]

    for plan_data in default_plans:
        SubscriptionPlan.objects.get_or_create(
            name=plan_data['name'],
            defaults=plan_data
        )


def generate_invoice_number():
    """
    Generate unique invoice number.

    Returns:
        str: Invoice number
    """
    timestamp = timezone.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(3).upper()
    return f"INV-{timestamp}-{random_part}"


def validate_webhook_payload(payload):
    """
    Validate webhook payload format.

    Args:
        payload: Dictionary containing webhook data

    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = ['action', 'ticker', 'quantity']

    for field in required_fields:
        if field not in payload:
            return False, f"Missing required field: {field}"

    # Validate action
    if payload['action'] not in ['buy', 'sell']:
        return False, "Action must be 'buy' or 'sell'"

    # Validate quantity
    try:
        quantity = Decimal(str(payload['quantity']))
        if quantity <= 0:
            return False, "Quantity must be greater than 0"
    except (ValueError, TypeError):
        return False, "Invalid quantity format"

    # Validate price if provided
    if 'price' in payload and payload['price'] is not None:
        try:
            price = Decimal(str(payload['price']))
            if price <= 0:
                return False, "Price must be greater than 0"
        except (ValueError, TypeError):
            return False, "Invalid price format"

    return True, None