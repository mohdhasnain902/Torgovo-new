"""
API serializers for subscriptions app.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from ..models import (
    SubscriptionPlan, UserSubscription, CustomBotWebhook,
    ManagedBotPerformance
)
from users.serializers import UserSerializer


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for SubscriptionPlan model."""
    plan_type_display = serializers.CharField(source='get_plan_type_display', read_only=True)
    yearly_savings_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )
    subscriber_count = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'plan_type', 'plan_type_display', 'name', 'description',
            'features', 'tags', 'monthly_price', 'yearly_price', 'setup_fee',
            'max_trading_pairs', 'max_bots', 'guaranteed_monthly_return',
            'profit_share_percentage', 'min_investment', 'api_calls_per_day',
            'webhook_requests_per_hour', 'concurrent_bots', 'is_active',
            'is_public', 'is_featured', 'sort_order', 'display_color',
            'yearly_savings_percentage', 'subscriber_count', 'total_revenue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subscriber_count(self, obj):
        """Get number of active subscribers."""
        return obj.get_subscriber_count()

    def get_total_revenue(self, obj):
        """Get total revenue for this plan."""
        return obj.get_total_revenue(30)


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for UserSubscription model."""
    user = UserSerializer(read_only=True)
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    billing_cycle_display = serializers.CharField(source='get_billing_cycle_display', read_only=True)
    is_active_trial = serializers.BooleanField(read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)
    days_remaining = serializers.IntegerField(read_only=True)
    trial_days_remaining = serializers.IntegerField(read_only=True)
    usage_stats = serializers.SerializerMethodField()

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'plan', 'plan_id', 'status', 'status_display',
            'billing_cycle', 'billing_cycle_display', 'start_date', 'end_date',
            'trial_end_date', 'auto_renew', 'payment_method', 'last_payment_date',
            'next_billing_date', 'api_calls_used_today', 'webhook_requests_used_hour',
            'last_usage_reset', 'is_active_trial', 'is_currently_active',
            'days_remaining', 'trial_days_remaining', 'usage_stats',
            'subscription_config', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'last_payment_date', 'next_billing_date',
            'api_calls_used_today', 'webhook_requests_used_hour',
            'last_usage_reset', 'created_at', 'updated_at'
        ]

    def get_usage_stats(self, obj):
        """Get usage statistics for the subscription."""
        return {
            'api_calls_used': obj.api_calls_used_today,
            'api_calls_limit': obj.plan.api_calls_per_day,
            'api_calls_remaining': max(0, obj.plan.api_calls_per_day - obj.api_calls_used_today),
            'webhook_requests_used': obj.webhook_requests_used_hour,
            'webhook_requests_limit': obj.plan.webhook_requests_per_hour,
            'webhook_requests_remaining': max(0, obj.plan.webhook_requests_per_hour - obj.webhook_requests_used_hour),
        }

    def validate_plan_id(self, value):
        """Validate plan ID."""
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan")

    def validate(self, data):
        """Validate subscription data."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        trial_end_date = data.get('trial_end_date')

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError("End date must be after start date")

        if trial_end_date and start_date and trial_end_date <= start_date:
            raise serializers.ValidationError("Trial end date must be after start date")

        return data


class CustomBotWebhookSerializer(serializers.ModelSerializer):
    """Serializer for CustomBotWebhook model."""
    user = UserSerializer(read_only=True)
    subscription = UserSubscriptionSerializer(read_only=True)
    subscription_id = serializers.IntegerField(write_only=True)
    pair_config = serializers.PrimaryKeyRelatedField(
        queryset=trading_models.PairConfig.objects.all(),
        write_only=True
    )
    pair_config_details = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    tradingview_config = serializers.JSONField(read_only=True)

    class Meta:
        model = CustomBotWebhook
        fields = [
            'id', 'user', 'subscription', 'subscription_id', 'pair_config',
            'pair_config_details', 'webhook_name', 'webhook_url', 'webhook_secret',
            'tradingview_config', 'is_active', 'last_triggered', 'total_triggers',
            'successful_triggers', 'success_rate', 'last_ip_address',
            'allow_ip_whitelist', 'allowed_ips', 'require_signature',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'webhook_url', 'webhook_secret', 'last_triggered',
            'total_triggers', 'successful_triggers', 'last_ip_address',
            'created_at', 'updated_at'
        ]

    def __init__(self, *args, **kwargs):
        """Initialize serializer with import of trading models."""
        super().__init__(*args, **kwargs)
        global trading_models
        from trading import models as trading_models

    def get_pair_config_details(self, obj):
        """Get pair configuration details."""
        return {
            'id': obj.pair_config.id,
            'name': obj.pair_config.name,
            'pair_symbol': obj.pair_config.pair_symbol,
            'exchange': obj.pair_config.exchange,
            'exchange_display': obj.pair_config.get_exchange_display()
        }

    def get_success_rate(self, obj):
        """Calculate success rate."""
        if obj.total_triggers > 0:
            return round((obj.successful_triggers / obj.total_triggers) * 100, 2)
        return 0

    def validate_subscription_id(self, value):
        """Validate subscription ID."""
        try:
            subscription = UserSubscription.objects.get(
                id=value,
                is_currently_active=True
            )
            return value
        except UserSubscription.DoesNotExist:
            raise serializers.ValidationError("Subscription not found or not active")

    def validate_pair_config(self, value):
        """Validate pair configuration."""
        if not value.is_active:
            raise serializers.ValidationError("Pair configuration is not active")
        return value

    def validate_allowed_ips(self, value):
        """Validate allowed IPs format."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Allowed IPs must be a list")

        # Basic IP validation
        import ipaddress
        for ip in value:
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise serializers.ValidationError(f"Invalid IP address: {ip}")

        return value


class CustomBotWebhookCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating CustomBotWebhook."""
    webhook_name = serializers.CharField(max_length=100)
    pair_config_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = CustomBotWebhook
        fields = [
            'webhook_name', 'pair_config_id', 'allow_ip_whitelist',
            'allowed_ips', 'require_signature'
        ]

    def __init__(self, *args, **kwargs):
        """Initialize serializer with import of trading models."""
        super().__init__(*args, **kwargs)
        global trading_models
        from trading import models as trading_models

    def validate_pair_config_id(self, value):
        """Validate pair configuration ID."""
        try:
            pair_config = trading_models.PairConfig.objects.get(id=value, is_active=True)
            return pair_config
        except trading_models.PairConfig.DoesNotExist:
            raise serializers.ValidationError("Pair configuration not found or not active")

    def create(self, validated_data):
        """Create webhook with generated secret and URL."""
        from ..utils import generate_webhook_secret, generate_webhook_url, generate_tradingview_config

        user = self.context['request'].user
        pair_config = validated_data.pop('pair_config_id')

        # Get active subscription
        subscription = UserSubscription.objects.filter(
            user=user,
            status='active',
            end_date__gte=timezone.now()
        ).first()

        if not subscription:
            raise serializers.ValidationError("No active subscription found")

        # Generate webhook secret and URL
        webhook_secret = generate_webhook_secret()
        webhook_url = generate_webhook_url(webhook_secret)
        tradingview_config = generate_tradingview_config(webhook_secret)

        webhook = CustomBotWebhook.objects.create(
            user=user,
            subscription=subscription,
            pair_config=pair_config,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            tradingview_config=tradingview_config,
            **validated_data
        )

        return webhook


class ManagedBotPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for ManagedBotPerformance model."""
    user = UserSerializer(read_only=True)
    subscription = UserSubscriptionSerializer(read_only=True)
    managed_bot = serializers.SerializerMethodField()
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_return = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    net_return_percentage = serializers.DecimalField(max_digits=8, decimal_places=4, read_only=True)
    profit_share_remaining = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = ManagedBotPerformance
        fields = [
            'id', 'user', 'subscription', 'managed_bot', 'initial_investment',
            'current_balance', 'current_value', 'total_profit', 'total_loss',
            'net_profit', 'profit_percentage', 'net_return', 'net_return_percentage',
            'profit_share_paid', 'profit_share_owed', 'profit_share_remaining',
            'max_drawdown', 'max_drawdown_percentage', 'total_trades',
            'winning_trades', 'losing_trades', 'win_rate', 'daily_returns',
            'weekly_returns', 'monthly_returns', 'last_calculated', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'current_balance', 'total_profit', 'total_loss',
            'net_profit', 'profit_percentage', 'profit_share_paid', 'profit_share_owed',
            'max_drawdown', 'max_drawdown_percentage', 'total_trades',
            'winning_trades', 'losing_trades', 'win_rate', 'daily_returns',
            'weekly_returns', 'monthly_returns', 'last_calculated', 'created_at'
        ]

    def get_managed_bot(self, obj):
        """Get managed bot details."""
        return {
            'id': obj.managed_bot.id,
            'name': obj.managed_bot.name,
            'pair_symbol': obj.managed_bot.pair_symbol,
            'exchange': obj.managed_bot.exchange,
            'exchange_display': obj.managed_bot.get_exchange_display(),
            'strategy_type': obj.managed_bot.strategy_type,
            'guaranteed_monthly_return': obj.managed_bot.guaranteed_monthly_return,
            'profit_share_percentage': obj.managed_bot.profit_share_percentage
        }


class ManagedBotPerformanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ManagedBotPerformance."""
    managed_bot_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ManagedBotPerformance
        fields = ['managed_bot_id', 'initial_investment']

    def __init__(self, *args, **kwargs):
        """Initialize serializer with import of trading models."""
        super().__init__(*args, **kwargs)
        global trading_models
        from trading import models as trading_models

    def validate_managed_bot_id(self, value):
        """Validate managed bot ID."""
        try:
            managed_bot = trading_models.PairConfig.objects.get(
                id=value,
                is_managed=True,
                is_active=True
            )
            return managed_bot
        except trading_models.PairConfig.DoesNotExist:
            raise serializers.ValidationError("Managed bot not found or not active")

    def validate_initial_investment(self, value):
        """Validate initial investment amount."""
        if value <= 0:
            raise serializers.ValidationError("Initial investment must be greater than 0")

        # Check against minimum investment if available
        if hasattr(self, 'managed_bot') and self.managed_bot.min_investment:
            if value < self.managed_bot.min_investment:
                raise serializers.ValidationError(
                    f"Initial investment must be at least {self.managed_bot.min_investment} USDT"
                )

        return value

    def create(self, validated_data):
        """Create managed bot performance record."""
        user = self.context['request'].user
        managed_bot = validated_data.pop('managed_bot_id')

        # Get active subscription
        subscription = UserSubscription.objects.filter(
            user=user,
            status='active',
            end_date__gte=timezone.now(),
            plan__plan_type='managed_bot'
        ).first()

        if not subscription:
            raise serializers.ValidationError("No active managed bot subscription found")

        # Check if performance record already exists
        try:
            performance = ManagedBotPerformance.objects.get(
                user=user,
                subscription=subscription,
                managed_bot=managed_bot
            )
            raise serializers.ValidationError("Performance record already exists for this bot")
        except ManagedBotPerformance.DoesNotExist:
            # Create new performance record
            performance = ManagedBotPerformance.objects.create(
                user=user,
                subscription=subscription,
                managed_bot=managed_bot,
                current_balance=validated_data['initial_investment'],
                **validated_data
            )

        return performance


class WebhookPayloadSerializer(serializers.Serializer):
    """Serializer for validating TradingView webhook payloads."""
    action = serializers.ChoiceField(choices=['buy', 'sell'])
    ticker = serializers.CharField(max_length=20)
    price = serializers.DecimalField(max_digits=15, decimal_places=8, required=False)
    quantity = serializers.DecimalField(max_digits=15, decimal_places=8)
    secret = serializers.CharField(max_length=100, required=False)

    class Meta:
        fields = ['action', 'ticker', 'price', 'quantity', 'secret']

    def validate_quantity(self, value):
        """Validate quantity."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value

    def validate_price(self, value):
        """Validate price."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value


class SubscriptionUsageSerializer(serializers.Serializer):
    """Serializer for subscription usage information."""
    api_calls_used = serializers.IntegerField(read_only=True)
    api_calls_limit = serializers.IntegerField(read_only=True)
    api_calls_remaining = serializers.IntegerField(read_only=True)
    webhook_requests_used = serializers.IntegerField(read_only=True)
    webhook_requests_limit = serializers.IntegerField(read_only=True)
    webhook_requests_remaining = serializers.IntegerField(read_only=True)
    bots_used = serializers.IntegerField(read_only=True)
    bots_limit = serializers.IntegerField(read_only=True)
    pairs_used = serializers.IntegerField(read_only=True)
    pairs_limit = serializers.IntegerField(read_only=True)


class PerformanceSummarySerializer(serializers.Serializer):
    """Serializer for performance summary."""
    period_days = serializers.IntegerField()
    total_invested = serializers.DecimalField(max_digits=15, decimal_places=2)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_loss = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_percentage = serializers.DecimalField(max_digits=8, decimal_places=4)
    total_trades = serializers.IntegerField()
    winning_trades = serializers.IntegerField()
    losing_trades = serializers.IntegerField()
    win_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    bot_breakdown = serializers.ListField(read_only=True)


class ManagedBotRankingSerializer(serializers.Serializer):
    """Serializer for managed bot rankings."""
    bot_id = serializers.IntegerField()
    bot_name = serializers.CharField()
    pair_symbol = serializers.CharField()
    exchange = serializers.CharField()
    strategy_type = serializers.CharField()
    total_subscribers = serializers.IntegerField()
    total_invested = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_performance = serializers.DecimalField(max_digits=8, decimal_places=4)
    total_trades = serializers.IntegerField()