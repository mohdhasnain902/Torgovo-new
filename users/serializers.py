"""
Serializers for users app.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    user = UserSerializer(read_only=True)
    exchange_display = serializers.CharField(source='get_exchange_display', read_only=True)
    is_active_trader = serializers.BooleanField(read_only=True)
    total_traded_volume = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    profit_loss_summary = serializers.JSONField(read_only=True)

    # Write-only fields for sensitive data
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'exchange', 'exchange_display', 'api_key', 'api_secret',
            'demo_mode', 'timezone', 'leverage', 'max_position_size',
            'email_notifications', 'trade_notifications', 'profit_loss_notifications',
            'max_daily_loss', 'stop_loss_percentage', 'take_profit_percentage',
            'created_at', 'updated_at', 'last_login_ip',
            'is_active_trader', 'total_traded_volume', 'profit_loss_summary'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login_ip']

    def validate_leverage(self, value):
        """Validate leverage value."""
        if value < 1 or value > 100:
            raise serializers.ValidationError("Leverage must be between 1 and 100.")
        return value

    def validate_max_position_size(self, value):
        """Validate max position size."""
        if value <= 0:
            raise serializers.ValidationError("Max position size must be greater than 0.")
        return value

    def validate_stop_loss_percentage(self, value):
        """Validate stop loss percentage."""
        if value < 0 or value > 50:
            raise serializers.ValidationError("Stop loss percentage must be between 0 and 50.")
        return value

    def validate_take_profit_percentage(self, value):
        """Validate take profit percentage."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Take profit percentage must be between 0 and 100.")
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile (excludes sensitive fields)."""

    class Meta:
        model = UserProfile
        fields = [
            'exchange', 'demo_mode', 'timezone', 'leverage', 'max_position_size',
            'email_notifications', 'trade_notifications', 'profit_loss_notifications',
            'max_daily_loss', 'stop_loss_percentage', 'take_profit_percentage'
        ]

    def validate_leverage(self, value):
        """Validate leverage value."""
        if value < 1 or value > 100:
            raise serializers.ValidationError("Leverage must be between 1 and 100.")
        return value

    def validate_max_position_size(self, value):
        """Validate max position size."""
        if value <= 0:
            raise serializers.ValidationError("Max position size must be greater than 0.")
        return value

    def validate_stop_loss_percentage(self, value):
        """Validate stop loss percentage."""
        if value < 0 or value > 50:
            raise serializers.ValidationError("Stop loss percentage must be between 0 and 50.")
        return value

    def validate_take_profit_percentage(self, value):
        """Validate take profit percentage."""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Take profit percentage must be between 0 and 100.")
        return value


class ExchangeCredentialsSerializer(serializers.ModelSerializer):
    """Serializer for updating exchange API credentials."""

    class Meta:
        model = UserProfile
        fields = ['exchange', 'api_key', 'api_secret', 'demo_mode']
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True},
        }

    def validate(self, data):
        """Validate that both API key and secret are provided if one is provided."""
        api_key = data.get('api_key')
        api_secret = data.get('api_secret')

        # If either field is provided, both should be provided
        if (api_key and not api_secret) or (api_secret and not api_key):
            raise serializers.ValidationError(
                "Both API key and API secret must be provided together."
            )

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        """Validate that passwords match."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return data

    def create(self, validated_data):
        """Create user and profile."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        # UserProfile will be created automatically via signal
        return user


class UserStatisticsSerializer(serializers.Serializer):
    """Serializer for user trading statistics."""
    total_traded_volume = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    active_subscriptions = serializers.IntegerField()
    is_active_trader = serializers.BooleanField()
    profit_loss_summary = UserProfileSerializer().fields['profit_loss_summary']