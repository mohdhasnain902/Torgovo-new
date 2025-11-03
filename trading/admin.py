"""
Admin configuration for trading app.
"""
from django.contrib import admin
from .models import PairConfig, Order, Indicator, BotSession


@admin.register(PairConfig)
class PairConfigAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'pair_symbol', 'exchange', 'bot_type', 'strategy_type',
        'is_active', 'is_public', 'min_investment', 'created_at'
    )
    list_filter = (
        'exchange', 'bot_type', 'strategy_type', 'is_active',
        'is_public', 'is_managed', 'symbol_type'
    )
    search_fields = ('name', 'pair_symbol', 'description', 'tags')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ()

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'pair_symbol', 'exchange', 'symbol_type', 'description')
        }),
        ('Bot Configuration', {
            'fields': ('bot_type', 'strategy_type', 'is_active', 'is_public')
        }),
        ('Trading Parameters', {
            'fields': (
                'min_order_size', 'max_order_size', 'default_quantity',
                'price_precision', 'quantity_precision'
            )
        }),
        ('Risk Management', {
            'fields': (
                'max_leverage', 'stop_loss_percentage', 'take_profit_percentage',
                'max_drawdown_percentage'
            )
        }),
        ('Managed Bot Settings', {
            'fields': (
                'is_managed', 'guaranteed_monthly_return',
                'profit_share_percentage', 'min_investment'
            ),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('bot_config', 'indicator_settings', 'tags'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'pair_config', 'action', 'order_type', 'quantity',
        'price', 'status', 'source', 'created_at'
    )
    list_filter = (
        'action', 'order_type', 'status', 'source', 'pair_config__exchange',
        'created_at'
    )
    search_fields = ('user__username', 'pair_config__pair_symbol', 'exchange_order_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'executed_at')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'user', 'pair_config', 'status', 'source')
        }),
        ('Order Details', {
            'fields': ('action', 'order_type', 'quantity', 'price', 'notes')
        }),
        ('Execution Details', {
            'fields': (
                'executed_price', 'executed_quantity', 'exchange_order_id',
                'executed_at'
            ),
            'classes': ('collapse',)
        }),
        ('Webhook Information', {
            'fields': ('webhook_secret',),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('order_config',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'pair_config'
        )


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'indicator_type', 'pair_config', 'is_active',
        'priority', 'created_at'
    )
    list_filter = (
        'indicator_type', 'is_active', 'priority', 'pair_config__exchange'
    )
    search_fields = ('name', 'pair_config__name', 'pair_config__pair_symbol')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ()

    fieldsets = (
        ('Indicator Information', {
            'fields': ('name', 'indicator_type', 'pair_config', 'is_active', 'priority')
        }),
        ('Parameters', {
            'fields': ('parameters', 'timeframes')
        }),
        ('Signal Generation', {
            'fields': ('buy_signal_condition', 'sell_signal_condition')
        }),
        ('Thresholds', {
            'fields': (
                'overbought_threshold', 'oversold_threshold',
                'signal_strength'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pair_config')


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_id', 'user', 'pair_config', 'bot_type', 'status',
        'total_orders', 'successful_orders', 'total_profit_loss', 'started_at'
    )
    list_filter = (
        'bot_type', 'status', 'pair_config__exchange', 'started_at'
    )
    search_fields = ('user__username', 'pair_config__name', 'session_id')
    readonly_fields = ('session_id', 'started_at', 'stopped_at', 'last_activity')
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'user', 'pair_config', 'bot_type', 'status')
        }),
        ('Configuration', {
            'fields': ('session_config', 'webhook_url')
        }),
        ('Statistics', {
            'fields': (
                'total_orders', 'successful_orders', 'failed_orders',
                'total_profit_loss'
            )
        }),
        ('Timestamps', {
            'fields': ('started_at', 'stopped_at', 'last_activity')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'pair_config'
        )