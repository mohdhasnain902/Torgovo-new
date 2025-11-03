"""
Serializers for trading app.
"""
from rest_framework import serializers
from .models import PairConfig, Order, BotSession


class PairConfigSerializer(serializers.ModelSerializer):
    """Serializer for PairConfig model."""
    exchange_display = serializers.CharField(source='get_exchange_display', read_only=True)
    bot_type_display = serializers.CharField(source='get_bot_type_display', read_only=True)
    strategy_type_display = serializers.CharField(source='get_strategy_type_display', read_only=True)

    class Meta:
        model = PairConfig
        fields = [
            'id', 'name', 'pair_symbol', 'exchange', 'exchange_display',
            'symbol_type', 'bot_type', 'bot_type_display', 'strategy_type',
            'strategy_type_display', 'min_order_size', 'max_order_size',
            'default_quantity', 'max_leverage', 'stop_loss_percentage',
            'take_profit_percentage', 'is_managed', 'guaranteed_monthly_return',
            'profit_share_percentage', 'min_investment', 'description',
            'tags', 'created_at', 'updated_at'
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model."""
    pair_config = PairConfigSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_value = serializers.DecimalField(max_digits=15, decimal_places=8, read_only=True)
    executed_total_value = serializers.DecimalField(max_digits=15, decimal_places=8, read_only=True)
    profit_loss = serializers.DecimalField(max_digits=15, decimal_places=8, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'pair_config', 'action', 'action_display',
            'order_type', 'order_type_display', 'quantity', 'price',
            'executed_price', 'executed_quantity', 'exchange_order_id',
            'status', 'status_display', 'source', 'notes',
            'total_value', 'executed_total_value', 'profit_loss',
            'created_at', 'updated_at', 'executed_at'
        ]


class BotSessionSerializer(serializers.ModelSerializer):
    """Serializer for BotSession model."""
    user = serializers.StringRelatedField(read_only=True)
    pair_config = PairConfigSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    bot_type_display = serializers.CharField(source='get_bot_type_display', read_only=True)

    class Meta:
        model = BotSession
        fields = [
            'session_id', 'user', 'pair_config', 'bot_type',
            'bot_type_display', 'status', 'status_display',
            'session_config', 'webhook_url', 'total_orders',
            'successful_orders', 'failed_orders', 'total_profit_loss',
            'started_at', 'stopped_at', 'last_activity'
        ]