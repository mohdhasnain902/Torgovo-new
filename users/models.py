"""
User models for crypto trading platform.
"""
import os
import secrets
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import base64


class EncryptedCharField(models.TextField):
    """
    Custom field for encrypting sensitive data like API keys.
    """
    description = "Encrypted character field"

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = kwargs.get('blank', True)
        kwargs['null'] = kwargs.get('null', True)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['blank']
        del kwargs['null']
        return name, path, args, kwargs

    def _get_encryption_key(self):
        """Get or create encryption key from settings."""
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            key = base64.urlsafe_b64encode(os.urandom(32))
            settings.FIELD_ENCRYPTION_KEY = key
        return key if isinstance(key, bytes) else key.encode()

    def _get_cipher(self):
        """Get Fernet cipher instance."""
        return Fernet(self._get_encryption_key())

    def from_db_value(self, value, expression, connection):
        """Decrypt value when loading from database."""
        if value is None:
            return value
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(value.encode()).decode()
        except Exception:
            # Return original value if decryption fails
            return value

    def get_prep_value(self, value):
        """Encrypt value before saving to database."""
        if value is None:
            return value
        try:
            cipher = self._get_cipher()
            return cipher.encrypt(value.encode()).decode()
        except Exception:
            # Return original value if encryption fails
            return value


class UserProfile(models.Model):
    """
    Extended user profile with exchange credentials and trading preferences.
    """
    EXCHANGE_CHOICES = [
        ('binance', 'Binance'),
        ('bybit', 'Bybit'),
        ('kraken', 'Kraken'),
        ('mexc', 'MEXC'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='trading_profile',
        verbose_name='User'
    )

    # Exchange API credentials (encrypted)
    exchange = models.CharField(
        max_length=20,
        choices=EXCHANGE_CHOICES,
        default='binance',
        verbose_name='Primary Exchange'
    )
    api_key = EncryptedCharField(
        max_length=255,
        verbose_name='API Key',
        help_text='Exchange API key (encrypted)'
    )
    api_secret = EncryptedCharField(
        max_length=255,
        verbose_name='API Secret',
        help_text='Exchange API secret (encrypted)'
    )

    # Trading preferences
    demo_mode = models.BooleanField(
        default=True,
        verbose_name='Demo Mode',
        help_text='Use demo/testnet for trading'
    )
    timezone = models.CharField(
        max_length=50,
        default='Asia/Karachi',
        verbose_name='Timezone'
    )
    leverage = models.IntegerField(
        default=1,
        verbose_name='Default Leverage',
        help_text='Default leverage for futures trading (1-100)'
    )
    max_position_size = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=1000.00,
        verbose_name='Max Position Size',
        help_text='Maximum position size in USDT'
    )

    # Notification preferences
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='Email Notifications'
    )
    trade_notifications = models.BooleanField(
        default=True,
        verbose_name='Trade Notifications'
    )
    profit_loss_notifications = models.BooleanField(
        default=True,
        verbose_name='Profit/Loss Notifications'
    )

    # Risk management
    max_daily_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Max Daily Loss',
        help_text='Maximum daily loss limit in USDT'
    )
    stop_loss_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        verbose_name='Stop Loss %',
        help_text='Default stop loss percentage'
    )
    take_profit_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        verbose_name='Take Profit %',
        help_text='Default take profit percentage'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['user', 'exchange']),
            models.Index(fields=['demo_mode']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_exchange_display()}"

    def clean(self):
        """Validate model data."""
        if self.leverage < 1 or self.leverage > 100:
            raise ValidationError({
                'leverage': 'Leverage must be between 1 and 100'
            })

        if self.max_position_size <= 0:
            raise ValidationError({
                'max_position_size': 'Max position size must be greater than 0'
            })

        if self.stop_loss_percentage < 0 or self.stop_loss_percentage > 50:
            raise ValidationError({
                'stop_loss_percentage': 'Stop loss percentage must be between 0 and 50'
            })

        if self.take_profit_percentage < 0 or self.take_profit_percentage > 100:
            raise ValidationError({
                'take_profit_percentage': 'Take profit percentage must be between 0 and 100'
            })

    @property
    def is_active_trader(self):
        """Check if user is actively trading."""
        from trading.models import Order
        from subscriptions.models import UserSubscription

        has_recent_orders = Order.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).exists()

        has_active_subscription = UserSubscription.objects.filter(
            user=self.user,
            status='active',
            end_date__gte=timezone.now()
        ).exists()

        return has_recent_orders or has_active_subscription

    @property
    def exchange_config(self):
        """Get exchange configuration for API."""
        from django.conf import settings

        exchange_key = self.exchange.lower()
        base_config = settings.EXCHANGE_CONFIG.get(exchange_key, {})

        if self.demo_mode and 'testnet_url' in base_config:
            base_url = base_config['testnet_url']
        else:
            base_url = base_config['api_url']

        return {
            'exchange': self.exchange,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'base_url': base_url,
            'demo_mode': self.demo_mode,
            'leverage': self.leverage,
        }

    def get_total_traded_volume(self):
        """Get total traded volume for this user."""
        from trading.models import Order
        from django.db.models import Sum

        result = Order.objects.filter(
            user=self.user,
            status='executed'
        ).aggregate(
            total_volume=Sum(models.F('price') * models.F('quantity'))
        )

        return result['total_volume'] or 0

    def get_profit_loss_summary(self):
        """Get profit/loss summary for this user."""
        from trading.models import Order
        from django.db.models import Sum, F

        # This is a simplified calculation
        # In production, you'd match buy/sell pairs properly
        executed_orders = Order.objects.filter(
            user=self.user,
            status='executed'
        )

        buy_orders = executed_orders.filter(action='buy')
        sell_orders = executed_orders.filter(action='sell')

        total_buy_value = buy_orders.aggregate(
            total=Sum(models.F('price') * models.F('quantity'))
        )['total'] or 0

        total_sell_value = sell_orders.aggregate(
            total=Sum(models.F('price') * models.F('quantity'))
        )['total'] or 0

        return {
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'gross_profit': total_sell_value - total_buy_value,
            'total_orders': executed_orders.count(),
            'buy_orders': buy_orders.count(),
            'sell_orders': sell_orders.count(),
        }


# Signal to create UserProfile when User is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for each new User."""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when User is saved."""
    if hasattr(instance, 'trading_profile'):
        instance.trading_profile.save()