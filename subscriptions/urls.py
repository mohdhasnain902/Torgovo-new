"""
URL configuration for subscriptions app.
"""
from django.urls import path, include

urlpatterns = [
    path('subscription-plans/', include('subscriptions.urls.subscription_plans')),
    path('', include('subscriptions.urls.user_subscriptions')),
    path('custom-bot/webhook/', include('subscriptions.urls.custom_bot_webhook')),
    path('managed-bot/', include('subscriptions.urls.managed_bot')),
]