"""
Trading models for crypto trading platform.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, F, Q
from decimal import Decimal
import json


class PairConfig(models.Model):
    """
    Configuration for trading pairs and bots.
    """
    EXCHANGE_CHOICES = [
        ('binance', 'Binance'),
        ('bybit', 'Bybit'),
        ('kraken', 'Kraken'),
        ('mexc', 'MEXC'),
    ]

    SYMBOL_TYPE_CHOICES = [
        ('spot', 'Spot Trading'),
        ('futures', 'Futures Trading'),
        ('swap', 'Perpetual Swap'),
    ]

    BOT_TYPE_CHOICES = [
        ('custom', 'Custom Bot'),
        ('managed', 'Managed Bot'),
        ('arbitrage', 'Arbitrage Bot'),
    ]

    STRATEGY_TYPE_CHOICES = [
        ('momentum', 'Momentum Strategy'),
        ('mean_reversion', 'Mean Reversion'),
        ('arbitrage', 'Arbitrage'),
        ('grid', 'Grid Trading'),
        ('dca', 'Dollar Cost Averaging'),
        ('scalping', 'Scalping'),
    ]

    # Basic configuration
    name = models.CharField(max_length=100, verbose_name='Bot Name')
    pair_symbol = models.CharField(max_length=20, verbose_name='Trading Pair')
    exchange = models.CharField(max_length=20, choices=EXCHANGE_CHOICES, verbose_name='Exchange')
    symbol_type = models.CharField(max_length=20, choices=SYMBOL_TYPE_CHOICES, default='spot')
    bot_type = models.CharField(max_length=20, choices=BOT_TYPE_CHOICES, default='custom')
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPE_CHOICES)

    # Trading parameters
    min_order_size = models.DecimalField(max_digits=15, decimal_places=8, verbose_name='Min Order Size')
    max_order_size = models.DecimalField(max_digits=15, decimal_places=8, verbose_name='Max Order Size')
    default_quantity = models.DecimalField(max_digits=15, decimal_places=8, verbose_name='Default Quantity')
    price_precision = models.IntegerField(default=8, verbose_name='Price Precision')
    quantity_precision = models.IntegerField(default=8, verbose_name='Quantity Precision')

    # Risk management
    max_leverage = models.IntegerField(default=1, verbose_name='Max Leverage')
    stop_loss_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    take_profit_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    max_drawdown_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=20.0)

    # Bot configuration (JSON field for flexible settings)
    bot_config = models.JSONField(default=dict, verbose_name='Bot Configuration')
    indicator_settings = models.JSONField(default=dict, verbose_name='Indicator Settings')

    # Performance tracking for managed bots
    is_managed = models.BooleanField(default=False, verbose_name='Is Managed Bot')
    guaranteed_monthly_return = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Guaranteed Monthly Return (%)'
    )
    profit_share_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Profit Share Percentage'
    )
    min_investment = models.DecimalField(
        max_digits=15, decimal_places=2, default=1000.00,
        verbose_name='Minimum Investment'
    )

    # Status and metadata
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True, verbose_name='Publicly Available')
    description = models.TextField(blank=True, verbose_name='Description')
    tags = models.JSONField(default=list, verbose_name='Tags')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trading Pair Configuration'
        verbose_name_plural = 'Trading Pair Configurations'
        unique_together = ['pair_symbol', 'exchange', 'symbol_type']
        indexes = [
            models.Index(fields=['exchange', 'pair_symbol']),
            models.Index(fields=['bot_type', 'is_active']),
            models.Index(fields=['is_managed', 'is_public']),
            models.Index(fields=['strategy_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.pair_symbol} - {self.get_exchange_display()})"

    def clean(self):
        """Validate model data."""
        if self.min_order_size <= 0:
            raise ValidationError('Min order size must be greater than 0')
        if self.max_order_size <= 0:
            raise ValidationError('Max order size must be greater than 0')
        if self.max_order_size < self.min_order_size:
            raise ValidationError('Max order size must be greater than min order size')
        if self.max_leverage < 1 or self.max_leverage > 100:
            raise ValidationError('Max leverage must be between 1 and 100')

    @property
    def current_price(self):
        """Get current price for this pair (placeholder - implement with real API)."""
        # This would integrate with exchange API to get current price
        return None

    def get_performance_metrics(self, days=30):
        """Get performance metrics for this pair config."""
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)

        orders = Order.objects.filter(
            pair_config=self,
            created_at__gte=start_date,
            created_at__lte=end_date,
            status='executed'
        )

        total_volume = orders.aggregate(
            total=Sum(F('price') * F('quantity'))
        )['total'] or Decimal('0')

        return {
            'period_days': days,
            'total_orders': orders.count(),
            'total_volume': total_volume,
            'buy_orders': orders.filter(action='buy').count(),
            'sell_orders': orders.filter(action='sell').count(),
            # Add more performance metrics as needed
        }


class Order(models.Model):
    """
    Individual trading orders.
    """
    ACTION_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]

    ORDER_TYPE_CHOICES = [
        ('market', 'Market Order'),
        ('limit', 'Limit Order'),
        ('stop_loss', 'Stop Loss'),
        ('take_profit', 'Take Profit'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('executed', 'Executed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]

    # Basic order information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    pair_config = models.ForeignKey(PairConfig, on_delete=models.CASCADE, related_name='orders')

    # Order details
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='market')
    quantity = models.DecimalField(max_digits=15, decimal_places=8)
    price = models.DecimalField(max_digits=15, decimal_places=8)

    # Executed details (filled when order is executed)
    executed_price = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    executed_quantity = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    exchange_order_id = models.CharField(max_length=100, null=True, blank=True)

    # Order metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    source = models.CharField(max_length=50, default='manual')  # manual, webhook, bot
    webhook_secret = models.CharField(max_length=100, null=True, blank=True)  # For webhook orders

    # Optional order notes and configuration
    notes = models.TextField(blank=True)
    order_config = models.JSONField(default=dict, verbose_name='Order Configuration')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Trading Order'
        verbose_name_plural = 'Trading Orders'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['pair_config', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['webhook_secret']),
            models.Index(fields=['source']),
        ]

    def __str__(self):
        return f"{self.action.upper()} {self.quantity} {self.pair_config.pair_symbol} @ {self.price}"

    @property
    def total_value(self):
        """Get total order value (price * quantity)."""
        return self.price * self.quantity

    @property
    def executed_total_value(self):
        """Get executed total value."""
        if self.executed_price and self.executed_quantity:
            return self.executed_price * self.executed_quantity
        return Decimal('0')

    def execute_order(self, executed_price=None, executed_quantity=None, exchange_order_id=None):
        """Execute the order."""
        self.status = 'executed'
        self.executed_at = timezone.now()
        if executed_price:
            self.executed_price = executed_price
        if executed_quantity:
            self.executed_quantity = executed_quantity
        if exchange_order_id:
            self.exchange_order_id = exchange_order_id
        self.save()

    def cancel_order(self):
        """Cancel the order."""
        self.status = 'cancelled'
        self.save()

    def get_profit_loss(self):
        """
        Calculate profit/loss for this order.
        For sell orders, match with corresponding buy orders.
        """
        if self.action != 'sell':
            return Decimal('0')

        # Find matching buy orders (FIFO - First In, First Out)
        buy_orders = Order.objects.filter(
            user=self.user,
            pair_config=self.pair_config,
            action='buy',
            status='executed'
        ).exclude(id=self.id).order_by('created_at')

        # Simple FIFO calculation (simplified for this example)
        if buy_orders.exists():
            buy_order = buy_orders.first()
            if buy_order.executed_price:
                profit_loss = (self.executed_price - buy_order.executed_price) * self.executed_quantity
                return profit_loss

        return Decimal('0')


class Indicator(models.Model):
    """
    Technical indicators and strategies for trading bots.
    """
    INDICATOR_TYPES = [
        ('RSI', 'Relative Strength Index'),
        ('MACD', 'MACD'),
        ('BOLLINGER', 'Bollinger Bands'),
        ('SMA', 'Simple Moving Average'),
        ('EMA', 'Exponential Moving Average'),
        ('STOCH', 'Stochastic Oscillator'),
        ('ADX', 'Average Directional Index'),
        ('ATR', 'Average True Range'),
        ('CCI', 'Commodity Channel Index'),
        ('WILLIAMS', 'Williams %R'),
        ('CUSTOM', 'Custom Indicator'),
    ]

    name = models.CharField(max_length=100, verbose_name='Indicator Name')
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_TYPES)
    pair_config = models.ForeignKey(PairConfig, on_delete=models.CASCADE, related_name='indicators')

    # Indicator parameters
    parameters = models.JSONField(default=dict, verbose_name='Indicator Parameters')
    timeframes = models.JSONField(default=list, verbose_name='Timeframes')

    # Signal generation
    buy_signal_condition = models.TextField(blank=True, verbose_name='Buy Signal Condition')
    sell_signal_condition = models.TextField(blank=True, verbose_name='Sell Signal Condition')

    # Thresholds and limits
    overbought_threshold = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    oversold_threshold = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    signal_strength = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)

    # Status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text='Higher priority indicators are checked first')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trading Indicator'
        verbose_name_plural = 'Trading Indicators'
        indexes = [
            models.Index(fields=['pair_config', 'is_active']),
            models.Index(fields=['indicator_type']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_indicator_type_display()})"

    def generate_signal(self, price_data):
        """
        Generate trading signal based on price data and indicator configuration.
        This is a placeholder - implement actual indicator calculations.
        """
        # Implement actual indicator logic here
        # This would calculate RSI, MACD, etc. based on price_data
        return {
            'signal': None,  # 'buy', 'sell', or None
            'strength': self.signal_strength,
            'confidence': 0.0,  # 0.0 to 1.0
            'metadata': {}
        }


class BotSession(models.Model):
    """
    Trading bot sessions for tracking bot lifecycle.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bot_sessions')
    pair_config = models.ForeignKey(PairConfig, on_delete=models.CASCADE, related_name='bot_sessions')

    # Session details
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot_type = models.CharField(max_length=20, choices=PairConfig.BOT_TYPE_CHOICES)

    # Session status
    status = models.CharField(max_length=20, choices=[
        ('starting', 'Starting'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ], default='starting')

    # Session configuration
    session_config = models.JSONField(default=dict, verbose_name='Session Configuration')
    webhook_url = models.URLField(blank=True, verbose_name='Webhook URL')

    # Session statistics
    total_orders = models.IntegerField(default=0)
    successful_orders = models.IntegerField(default=0)
    failed_orders = models.IntegerField(default=0)
    total_profit_loss = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bot Session'
        verbose_name_plural = 'Bot Sessions'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['pair_config', 'status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.pair_config.name} ({self.status})"

    def start_session(self):
        """Start the bot session."""
        self.status = 'running'
        self.save()

    def stop_session(self):
        """Stop the bot session."""
        self.status = 'stopped'
        self.stopped_at = timezone.now()
        self.save()

    def increment_order_count(self, success=True):
        """Increment order statistics."""
        self.total_orders += 1
        if success:
            self.successful_orders += 1
        else:
            self.failed_orders += 1
        self.last_activity = timezone.now()
        self.save()

    def update_profit_loss(self, profit_loss_amount):
        """Update total profit/loss for the session."""
        self.total_profit_loss += profit_loss_amount
        self.save()