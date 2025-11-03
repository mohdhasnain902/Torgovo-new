"""
Admin configuration for subscriptions app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import SubscriptionPlan, UserSubscription, CustomBotWebhook, ManagedBotPerformance


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'plan_type', 'monthly_price', 'is_active', 'is_public',
        'is_featured', 'max_trading_pairs', 'guaranteed_monthly_return',
        'created_at'
    )
    list_filter = (
        'plan_type', 'is_active', 'is_public', 'is_featured',
        'created_at'
    )
    search_fields = ('name', 'description', 'features')
    readonly_fields = ('created_at', 'updated_at', 'get_subscriber_count_display')
    filter_horizontal = ()

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'plan_type', 'description', 'features', 'tags'
            )
        }),
        ('Pricing', {
            'fields': (
                'monthly_price', 'yearly_price', 'setup_fee',
                'get_subscriber_count_display'
            )
        }),
        ('Custom Bot Limits', {
            'fields': (
                'max_trading_pairs', 'max_bots', 'concurrent_bots'
            ),
            'classes': ('collapse',)
        }),
        ('Managed Bot Settings', {
            'fields': (
                'guaranteed_monthly_return', 'profit_share_percentage',
                'min_investment'
            ),
            'classes': ('collapse',)
        }),
        ('Usage Limits', {
            'fields': (
                'api_calls_per_day', 'webhook_requests_per_hour'
            )
        }),
        ('Display Settings', {
            'fields': (
                'is_active', 'is_public', 'is_featured',
                'sort_order', 'display_color'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_subscriber_count_display(self, obj):
        """Display subscriber count."""
        count = obj.get_subscriber_count()
        return format_html('<span style="color: green;">{}</span> active', count)
    get_subscriber_count_display.short_description = 'Active Subscribers'


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'status', 'billing_cycle', 'start_date',
        'end_date', 'auto_renew', 'days_remaining', 'created_at'
    )
    list_filter = (
        'status', 'billing_cycle', 'plan__plan_type', 'auto_renew',
        'created_at', 'end_date'
    )
    search_fields = (
        'user__username', 'user__email', 'plan__name'
    )
    readonly_fields = (
        'created_at', 'updated_at', 'is_active_trial', 'is_currently_active',
        'days_remaining', 'trial_days_remaining'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Subscription Details', {
            'fields': (
                'user', 'plan', 'status', 'billing_cycle'
            )
        }),
        ('Subscription Period', {
            'fields': (
                'start_date', 'end_date', 'trial_end_date',
                'is_currently_active', 'days_remaining',
                'trial_days_remaining'
            )
        }),
        ('Billing Information', {
            'fields': (
                'auto_renew', 'payment_method', 'last_payment_date',
                'next_billing_date'
            )
        }),
        ('Usage Tracking', {
            'fields': (
                'api_calls_used_today', 'webhook_requests_used_hour',
                'last_usage_reset'
            )
        }),
        ('Configuration', {
            'fields': (
                'subscription_config', 'notes'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_active_trial(self, obj):
        """Check if subscription is in active trial."""
        return obj.is_active_trial
    is_active_trial.boolean = True
    is_active_trial.short_description = 'Active Trial'

    def is_currently_active(self, obj):
        """Check if subscription is currently active."""
        return obj.is_currently_active
    is_currently_active.boolean = True
    is_currently_active.short_description = 'Currently Active'

    def days_remaining(self, obj):
        """Get days remaining."""
        return obj.days_remaining
    days_remaining.short_description = 'Days Remaining'

    def trial_days_remaining(self, obj):
        """Get trial days remaining."""
        return obj.trial_days_remaining
    trial_days_remaining.short_description = 'Trial Days Remaining'


@admin.register(CustomBotWebhook)
class CustomBotWebhookAdmin(admin.ModelAdmin):
    list_display = (
        'webhook_name', 'user', 'pair_config', 'is_active',
        'total_triggers', 'successful_triggers', 'success_rate',
        'last_triggered', 'created_at'
    )
    list_filter = (
        'is_active', 'allow_ip_whitelist', 'require_signature',
        'created_at', 'last_triggered'
    )
    search_fields = (
        'webhook_name', 'user__username', 'pair_config__name',
        'webhook_secret'
    )
    readonly_fields = (
        'created_at', 'updated_at', 'webhook_url', 'success_rate'
    )

    fieldsets = (
        ('Webhook Information', {
            'fields': (
                'user', 'subscription', 'pair_config', 'webhook_name'
            )
        }),
        ('Webhook Configuration', {
            'fields': (
                'webhook_url', 'webhook_secret',
                'is_active', 'tradingview_config'
            )
        }),
        ('Usage Statistics', {
            'fields': (
                'total_triggers', 'successful_triggers', 'success_rate',
                'last_triggered'
            )
        }),
        ('Security Settings', {
            'fields': (
                'allow_ip_whitelist', 'allowed_ips',
                'require_signature', 'last_ip_address'
            )
        }),
        ('Rate Limiting', {
            'fields': (
                'rate_limit_count', 'rate_limit_reset'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def success_rate(self, obj):
        """Calculate success rate."""
        if obj.total_triggers > 0:
            rate = (obj.successful_triggers / obj.total_triggers) * 100
            color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, rate
            )
        return '-'
    success_rate.short_description = 'Success Rate'


@admin.register(ManagedBotPerformance)
class ManagedBotPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'managed_bot', 'initial_investment', 'current_balance',
        'net_profit', 'profit_percentage', 'win_rate', 'total_trades',
        'last_calculated', 'created_at'
    )
    list_filter = (
        'managed_bot__exchange', 'created_at', 'last_calculated'
    )
    search_fields = (
        'user__username', 'managed_bot__name', 'managed_bot__pair_symbol'
    )
    readonly_fields = (
        'created_at', 'last_calculated', 'current_value',
        'net_return', 'net_return_percentage', 'profit_share_remaining'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Performance Overview', {
            'fields': (
                'user', 'subscription', 'managed_bot',
                'initial_investment', 'current_balance',
                'current_value', 'net_return', 'net_return_percentage'
            )
        }),
        ('Profit & Loss', {
            'fields': (
                'total_profit', 'total_loss', 'net_profit',
                'profit_percentage'
            )
        }),
        ('Profit Sharing', {
            'fields': (
                'profit_share_paid', 'profit_share_owed',
                'profit_share_remaining'
            )
        }),
        ('Trading Statistics', {
            'fields': (
                'total_trades', 'winning_trades', 'losing_trades',
                'win_rate'
            )
        }),
        ('Risk Metrics', {
            'fields': (
                'max_drawdown', 'max_drawdown_percentage'
            )
        }),
        ('Performance Tracking', {
            'fields': (
                'daily_returns', 'weekly_returns', 'monthly_returns'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_calculated')
        }),
    )

    def current_value(self, obj):
        """Get current portfolio value."""
        return obj.current_value
    current_value.short_description = 'Current Value'

    def net_return(self, obj):
        """Get net return amount."""
        return obj.net_return
    net_return.short_description = 'Net Return'

    def net_return_percentage(self, obj):
        """Get net return percentage."""
        percentage = obj.net_return_percentage
        color = 'green' if percentage >= 0 else 'red'
        return format_html(
            '<span style="color: {};">{:.2f}%</span>',
            color, percentage
        )
    net_return_percentage.short_description = 'Net Return %'

    def profit_share_remaining(self, obj):
        """Get remaining profit share to be paid."""
        return obj.profit_share_remaining
    profit_share_remaining.short_description = 'Profit Share Remaining'