"""
Admin configuration for users app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Trading Profile'
    fields = (
        'exchange',
        'api_key',
        'api_secret',
        'demo_mode',
        'timezone',
        'leverage',
        'max_position_size',
        'email_notifications',
        'trade_notifications',
        'max_daily_loss',
        'stop_loss_percentage',
        'take_profit_percentage',
    )


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_exchange')
    list_select_related = ('trading_profile',)

    def get_exchange(self, obj):
        return obj.trading_profile.get_exchange_display() if hasattr(obj, 'trading_profile') else 'N/A'
    get_exchange.short_description = 'Exchange'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'exchange', 'demo_mode', 'leverage', 'max_position_size', 'is_active_trader', 'created_at')
    list_filter = ('exchange', 'demo_mode', 'email_notifications', 'trade_notifications', 'created_at')
    search_fields = ('user__username', 'user__email', 'exchange')
    readonly_fields = ('created_at', 'updated_at', 'last_login_ip', 'is_active_trader')

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'created_at', 'updated_at', 'last_login_ip')
        }),
        ('Exchange Configuration', {
            'fields': ('exchange', 'api_key', 'api_secret', 'demo_mode')
        }),
        ('Trading Preferences', {
            'fields': ('timezone', 'leverage', 'max_position_size')
        }),
        ('Risk Management', {
            'fields': ('max_daily_loss', 'stop_loss_percentage', 'take_profit_percentage')
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'trade_notifications', 'profit_loss_notifications')
        }),
        ('Statistics', {
            'fields': ('is_active_trader',),
            'classes': ('collapse',)
        }),
    )

    def is_active_trader(self, obj):
        return obj.is_active_trader
    is_active_trader.boolean = True
    is_active_trader.short_description = 'Active Trader'