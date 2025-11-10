"""
URL configuration for custom bot webhook endpoints.
"""
from django.urls import path
from subscriptions.api import views as api_views

app_name = 'custom_bot_webhook'

urlpatterns = [
    path('generate/', api_views.CustomBotWebhookCreateView.as_view(), name='generate'),
    path('', api_views.CustomBotWebhookListView.as_view(), name='list'),
    path('<int:pk>/', api_views.CustomBotWebhookDetailView.as_view(), name='detail'),
    path('receive/<str:webhook_secret>/', api_views.TradingViewWebhookView.as_view(), name='receive'),
    path('test/<str:webhook_secret>/', api_views.webhook_test, name='test'),
]