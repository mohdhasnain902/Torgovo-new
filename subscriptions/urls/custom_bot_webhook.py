"""
URL configuration for custom bot webhook endpoints.
"""
from django.urls import path
from . import views

app_name = 'custom_bot_webhook'

urlpatterns = [
    path('generate/', views.CustomBotWebhookCreateView.as_view(), name='generate'),
    path('', views.CustomBotWebhookListView.as_view(), name='list'),
    path('<int:pk>/', views.CustomBotWebhookDetailView.as_view(), name='detail'),
    path('receive/<str:webhook_secret>/', views.TradingViewWebhookView.as_view(), name='receive'),
    path('test/<str:webhook_secret>/', views.webhook_test, name='test'),
]