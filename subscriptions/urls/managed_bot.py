"""
URL configuration for managed bot endpoints.
"""
from django.urls import path
from subscriptions.api import views as api_views

app_name = 'managed_bot'

urlpatterns = [
    path('available/', api_views.available_managed_bots, name='available'),
    path('subscribe/', api_views.ManagedBotSubscribeView.as_view(), name='subscribe'),
    path('performance/', api_views.managed_bot_performance, name='performance'),
    path('rankings/', api_views.managed_bot_rankings, name='rankings'),
]