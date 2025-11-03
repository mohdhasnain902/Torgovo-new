"""
URL configuration for managed bot endpoints.
"""
from django.urls import path
from . import views

app_name = 'managed_bot'

urlpatterns = [
    path('available/', views.available_managed_bots, name='available'),
    path('subscribe/', views.ManagedBotSubscribeView.as_view(), name='subscribe'),
    path('performance/', views.managed_bot_performance, name='performance'),
    path('rankings/', views.managed_bot_rankings, name='rankings'),
]