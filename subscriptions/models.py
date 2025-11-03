"""
Subscription models for crypto trading platform.
"""
import uuid
import secrets
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, F, Q, Count
from trading.models import PairConfig, Order


class SubscriptionPlan(models.Model):
    """
    Available subscription plans for users.
    """
    PLAN_TYPES = [
        ('custom_bot', 'Custom Bot'),
        ('managed_bot', 'Managed Bot'),
    ]

    # Basic information
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
        verbose_name='Plan Type'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='Plan Name'
    )
    description = models.TextField(
        verbose_name='Description'
    )
    features = models.JSONField(
        default=dict,
        verbose_name='Features',
        help_text='Flexible feature list'
    )
    tags = models.JSONField(
        default=list,
        verbose_name='Tags',
        help_text='List of tags for categorization'
    )

    # Pricing
    monthly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monthly Price (USDT)'
    )
    yearly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Yearly Price (USDT)',
        help_text='Optional yearly discount pricing'
    )
    setup_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Setup Fee (USDT)'
    )

    # Custom bot specific fields
    max_trading_pairs = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Max Trading Pairs',
        help_text='Maximum number of trading pairs for custom bots'
    )
    max_bots = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Max Bots',
        help_text='Maximum number of active bots'
    )

    # Managed bot specific fields
    guaranteed_monthly_return = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Guaranteed Monthly Return (%)',
        help_text='For managed bots only (2-15%)'
    )
    profit_share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Profit Share Percentage',
        help_text='For managed bots only (20-50%)'
    )
    min_investment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Minimum Investment (USDT)',
        help_text='Minimum investment for managed bots'
    )

    # Plan limits and configuration
    api_calls_per_day = models.IntegerField(
        default=1000,
        verbose_name='API Calls Per Day'
    )
    webhook_requests_per_hour = models.IntegerField(
        default=100,
        verbose_name='Webhook Requests Per Hour'
    )
    concurrent_bots = models.IntegerField(
        default=1,
        verbose_name='Concurrent Bots'
    )

    # Status and visibility
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
    )
    is_public = models.BooleanField(
        default=True,
        verbose_name='Publicly Available'
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Featured Plan'
    )

    # Sorting and display
    sort_order = models.IntegerField(
        default=0,
        verbose_name='Sort Order'
    )
    display_color = models.CharField(
        max_length=20,
        default='#007bff',
        verbose_name='Display Color',
        help_text='Hex color code for UI display'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
        indexes = [
            models.Index(fields=['plan_type', 'is_active']),
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['monthly_price']),
            models.Index(fields=['sort_order']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"

    def clean(self):
        """Validate model data."""
        if self.plan_type == 'custom_bot' and self.max_trading_pairs is None:
            raise ValidationError({
                'max_trading_pairs': 'Custom bot plans must specify max trading pairs.'
            })

        if self.plan_type == 'managed_bot':
            if self.guaranteed_monthly_return is None:
                raise ValidationError({
                    'guaranteed_monthly_return': 'Managed bot plans must specify guaranteed monthly return.'
                })
            if self.profit_share_percentage is None:
                raise ValidationError({
                    'profit_share_percentage': 'Managed bot plans must specify profit share percentage.'
                })
            if self.min_investment is None:
                raise ValidationError({
                    'min_investment': 'Managed bot plans must specify minimum investment.'
                })

        if self.monthly_price <= 0:
            raise ValidationError({
                'monthly_price': 'Monthly price must be greater than 0.'
            })

        if self.yearly_price and self.yearly_price <= 0:
            raise ValidationError({
                'yearly_price': 'Yearly price must be greater than 0.'
            })

    @property
    def yearly_savings_percentage(self):
        """Calculate yearly savings percentage."""
        if not self.yearly_price:
            return 0
        yearly_cost_without_discount = self.monthly_price * 12
        savings = yearly_cost_without_discount - self.yearly_price
        return round((savings / yearly_cost_without_discount) * 100, 1) if yearly_cost_without_discount > 0 else 0

    def get_subscriber_count(self):
        """Get number of active subscribers."""
        return UserSubscription.objects.filter(
            plan=self,
            status='active',
            end_date__gte=timezone.now()
        ).count()

    def get_total_revenue(self, days=30):
        """Get total revenue for this plan in the last N days."""
        start_date = timezone.now() - timezone.timedelta(days=days)
        # This would integrate with payment system in Phase 2
        # For now, return calculated based on active subscriptions
        return 0


class UserSubscription(models.Model):
    """
    User's subscription to a plan.
    """
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    # User and plan relationship
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )

    # Subscription details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trial',
        verbose_name='Status'
    )
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly',
        verbose_name='Billing Cycle'
    )

    # Subscription period
    start_date = models.DateTimeField(
        verbose_name='Start Date'
    )
    end_date = models.DateTimeField(
        verbose_name='End Date'
    )
    trial_end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Trial End Date'
    )

    # Billing information
    auto_renew = models.BooleanField(
        default=False,
        verbose_name='Auto Renew'
    )
    payment_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Payment Method',
        help_text='For future payment integration'
    )
    last_payment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Payment Date'
    )
    next_billing_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Next Billing Date'
    )

    # Usage tracking
    api_calls_used_today = models.IntegerField(
        default=0,
        verbose_name='API Calls Used Today'
    )
    webhook_requests_used_hour = models.IntegerField(
        default=0,
        verbose_name='Webhook Requests Used This Hour'
    )
    last_usage_reset = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Last Usage Reset'
    )

    # Subscription metadata
    subscription_config = models.JSONField(
        default=dict,
        verbose_name='Subscription Configuration'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Notes'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'end_date']),
            models.Index(fields=['plan', 'status']),
            models.Index(fields=['auto_renew']),
            models.Index(fields=['next_billing_date']),
        ]
        unique_together = ['user', 'plan', 'status']

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"

    def clean(self):
        """Validate model data."""
        if self.end_date <= self.start_date:
            raise ValidationError({
                'end_date': 'End date must be after start date.'
            })

        if self.trial_end_date and self.trial_end_date <= self.start_date:
            raise ValidationError({
                'trial_end_date': 'Trial end date must be after start date.'
            })

    @property
    def is_active_trial(self):
        """Check if subscription is in active trial period."""
        return (
            self.status == 'trial' and
            self.trial_end_date and
            timezone.now() < self.trial_end_date
        )

    @property
    def is_currently_active(self):
        """Check if subscription is currently active."""
        return (
            self.status == 'active' and
            timezone.now() <= self.end_date
        )

    @property
    def days_remaining(self):
        """Get days remaining in current subscription period."""
        if self.is_currently_active:
            remaining = self.end_date - timezone.now()
            return max(0, remaining.days)
        return 0

    @property
    def trial_days_remaining(self):
        """Get days remaining in trial period."""
        if self.is_active_trial:
            remaining = self.trial_end_date - timezone.now()
            return max(0, remaining.days)
        return 0

    def extend_subscription(self, days=30):
        """Extend subscription by specified number of days."""
        if self.end_date >= timezone.now():
            self.end_date = self.end_date + timezone.timedelta(days=days)
        else:
            self.end_date = timezone.now() + timezone.timedelta(days=days)

        self.status = 'active'
        self.save()

    def cancel_subscription(self, immediate=False):
        """Cancel subscription."""
        if immediate:
            self.status = 'cancelled'
            self.auto_renew = False
        else:
            self.auto_renew = False

        self.save()

    def can_use_feature(self, feature_name):
        """Check if user can use a specific feature."""
        if not self.is_currently_active:
            return False

        # Check plan features
        plan_features = self.plan.features or {}
        return plan_features.get(feature_name, False)

    def check_usage_limits(self, api_calls=0, webhook_requests=0):
        """Check if user is within usage limits."""
        if not self.is_currently_active:
            return False, "Subscription not active"

        # Reset daily counters if needed
        self.reset_usage_counters()

        # Check API call limits
        if (self.api_calls_used_today + api_calls) > self.plan.api_calls_per_day:
            return False, f"API call limit exceeded ({self.plan.api_calls_per_day}/day)"

        # Check webhook request limits
        if (self.webhook_requests_used_hour + webhook_requests) > self.plan.webhook_requests_per_hour:
            return False, f"Webhook request limit exceeded ({self.plan.webhook_requests_per_hour}/hour)"

        return True, "Within limits"

    def reset_usage_counters(self):
        """Reset usage counters if needed."""
        now = timezone.now()
        last_reset = self.last_usage_reset

        # Reset daily counters
        if now.date() > last_reset.date():
            self.api_calls_used_today = 0
            self.last_usage_reset = now
            self.save()

        # Reset hourly counters (simplified - would need more precise tracking in production)
        if now.hour > last_reset.hour:
            self.webhook_requests_used_hour = 0
            self.save()

    def record_api_call(self):
        """Record an API call usage."""
        self.api_calls_used_today += 1
        self.save(update_fields=['api_calls_used_today'])

    def record_webhook_request(self):
        """Record a webhook request usage."""
        self.webhook_requests_used_hour += 1
        self.save(update_fields=['webhook_requests_used_hour'])


class CustomBotWebhook(models.Model):
    """
    Webhook configurations for custom trading bots.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='custom_bot_webhooks'
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='custom_bot_webhooks'
    )
    pair_config = models.ForeignKey(
        'trading.PairConfig',
        on_delete=models.CASCADE,
        related_name='custom_bot_webhooks'
    )

    # Webhook configuration
    webhook_url = models.URLField(
        max_length=500,
        unique=True,
        verbose_name='Webhook URL'
    )
    webhook_secret = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Webhook Secret'
    )
    webhook_name = models.CharField(
        max_length=100,
        verbose_name='Webhook Name'
    )

    # TradingView configuration
    tradingview_config = models.JSONField(
        default=dict,
        verbose_name='TradingView Configuration'
    )

    # Webhook status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Active'
    )
    last_triggered = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Triggered'
    )
    total_triggers = models.IntegerField(
        default=0,
        verbose_name='Total Triggers'
    )
    successful_triggers = models.IntegerField(
        default=0,
        verbose_name='Successful Triggers'
    )

    # Rate limiting and security
    last_ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Last IP Address'
    )
    rate_limit_count = models.IntegerField(
        default=0,
        verbose_name='Rate Limit Count'
    )
    rate_limit_reset = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Rate Limit Reset'
    )

    # Webhook configuration options
    allow_ip_whitelist = models.BooleanField(
        default=False,
        verbose_name='Enable IP Whitelist'
    )
    allowed_ips = models.JSONField(
        default=list,
        verbose_name='Allowed IP Addresses',
        help_text='List of allowed IP addresses'
    )
    require_signature = models.BooleanField(
        default=False,
        verbose_name='Require Signature'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Custom Bot Webhook'
        verbose_name_plural = 'Custom Bot Webhooks'
        indexes = [
            models.Index(fields=['webhook_secret']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['subscription', 'is_active']),
            models.Index(fields=['last_triggered']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.webhook_name} ({self.user.username})"

    def generate_webhook_config(self):
        """Generate TradingView webhook configuration."""
        base_url = "https://yourdomain.com"  # This should come from settings
        webhook_url = f"{base_url}/api/custom-bot/webhook/receive/{self.webhook_secret}/"

        tradingview_config = {
            "webhook_url": webhook_url,
            "tradingview_json": {
                "action": "{{strategy.order.action}}",
                "ticker": "{{ticker}}",
                "price": "{{close}}",
                "quantity": "{{strategy.order.contracts}}",
                "secret": self.webhook_secret
            }
        }

        self.tradingview_config = tradingview_config
        self.webhook_url = webhook_url
        self.save()

        return tradingview_config

    def check_rate_limit(self):
        """Check if webhook is within rate limits."""
        now = timezone.now()

        # Reset rate limit if needed (hourly reset)
        if self.rate_limit_reset and now > self.rate_limit_reset:
            self.rate_limit_count = 0
            self.rate_limit_reset = now + timezone.timedelta(hours=1)
            self.save()

        # Check rate limit (from subscription plan)
        max_requests = self.subscription.plan.webhook_requests_per_hour
        if self.rate_limit_count >= max_requests:
            return False, "Rate limit exceeded"

        return True, "Within rate limit"

    def record_trigger(self, success=True, ip_address=None):
        """Record a webhook trigger."""
        self.last_triggered = timezone.now()
        self.total_triggers += 1
        if success:
            self.successful_triggers += 1

        if ip_address:
            self.last_ip_address = ip_address

        # Update rate limiting
        self.rate_limit_count += 1
        if not self.rate_limit_reset:
            self.rate_limit_reset = timezone.now() + timezone.timedelta(hours=1)

        self.save()


class ManagedBotPerformance(models.Model):
    """
    Performance tracking for managed bot subscriptions.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='managed_bot_performances'
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='managed_bot_performances'
    )
    managed_bot = models.ForeignKey(
        'trading.PairConfig',
        on_delete=models.CASCADE,
        related_name='managed_bot_performances'
    )

    # Investment and performance tracking
    initial_investment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Initial Investment (USDT)'
    )
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Current Balance (USDT)'
    )
    total_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Total Profit (USDT)'
    )
    total_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Total Loss (USDT)'
    )
    profit_share_paid = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Profit Share Paid (USDT)'
    )
    profit_share_owed = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Profit Share Owed (USDT)'
    )

    # Performance metrics
    net_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Net Profit (USDT)'
    )
    profit_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0,
        verbose_name='Profit Percentage (%)'
    )
    max_drawdown = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Max Drawdown (USDT)'
    )
    max_drawdown_percentage = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0,
        verbose_name='Max Drawdown Percentage (%)'
    )

    # Trading statistics
    total_trades = models.IntegerField(
        default=0,
        verbose_name='Total Trades'
    )
    winning_trades = models.IntegerField(
        default=0,
        verbose_name='Winning Trades'
    )
    losing_trades = models.IntegerField(
        default=0,
        verbose_name='Losing Trades'
    )
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Win Rate (%)'
    )

    # Performance tracking over time
    daily_returns = models.JSONField(
        default=list,
        verbose_name='Daily Returns',
        help_text='List of daily return percentages'
    )
    weekly_returns = models.JSONField(
        default=list,
        verbose_name='Weekly Returns',
        help_text='List of weekly return percentages'
    )
    monthly_returns = models.JSONField(
        default=list,
        verbose_name='Monthly Returns',
        help_text='List of monthly return percentages'
    )

    # Timestamps
    last_calculated = models.DateTimeField(
        auto_now=True,
        verbose_name='Last Calculated'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )

    class Meta:
        verbose_name = 'Managed Bot Performance'
        verbose_name_plural = 'Managed Bot Performances'
        indexes = [
            models.Index(fields=['user', 'subscription']),
            models.Index(fields=['managed_bot', 'user']),
            models.Index(fields=['last_calculated']),
            models.Index(fields=['created_at']),
            models.Index(fields=['profit_percentage']),
        ]
        unique_together = ['user', 'subscription', 'managed_bot']

    def __str__(self):
        return f"{self.user.username} - {self.managed_bot.name} ({self.profit_percentage}%)"

    @property
    def current_value(self):
        """Get current portfolio value."""
        return self.current_balance

    @property
    def net_return(self):
        """Get net return amount."""
        return self.current_balance - self.initial_investment

    @property
    def net_return_percentage(self):
        """Get net return percentage."""
        if self.initial_investment > 0:
            return round((self.net_return / self.initial_investment) * 100, 4)
        return 0

    @property
    def profit_share_remaining(self):
        """Get remaining profit share to be paid."""
        return self.profit_share_owed - self.profit_share_paid

    def calculate_performance(self):
        """Recalculate performance metrics from orders."""
        from .utils import calculate_managed_bot_performance

        # Get calculated performance
        calculated = calculate_managed_bot_performance(self.user, self.managed_bot)

        # Update performance record
        self.total_profit = calculated['total_profit']
        self.total_loss = calculated['total_loss']
        self.current_balance = calculated['current_balance']
        self.net_profit = calculated['net_profit']
        self.profit_percentage = calculated['profit_percentage']

        # Calculate profit share
        from .utils import calculate_profit_share
        profit_share = calculate_profit_share(self.user, self.managed_bot)
        self.profit_share_owed = profit_share['profit_share_owed']

        # Calculate win rate
        if self.total_trades > 0:
            self.win_rate = round((self.winning_trades / self.total_trades) * 100, 2)

        self.save()

    def record_trade(self, profit_loss_amount):
        """Record a trade and update performance."""
        self.total_trades += 1

        if profit_loss_amount > 0:
            self.total_profit += profit_loss_amount
            self.winning_trades += 1
        else:
            self.total_loss += abs(profit_loss_amount)
            self.losing_trades += 1

        # Recalculate net metrics
        self.net_profit = self.total_profit - self.total_loss
        self.current_balance = self.initial_investment + self.net_profit

        if self.initial_investment > 0:
            self.profit_percentage = round((self.net_profit / self.initial_investment) * 100, 4)

        # Recalculate win rate
        if self.total_trades > 0:
            self.win_rate = round((self.winning_trades / self.total_trades) * 100, 2)

        self.save()

    def get_performance_summary(self, period_days=30):
        """Get performance summary for a specific period."""
        from .utils import get_performance_summary

        return get_performance_summary(self.user, period_days)