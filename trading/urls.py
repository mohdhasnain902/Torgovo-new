"""
URL configuration for trading app.
"""
from django.urls import path
from . import views

app_name = 'trading'

urlpatterns = [
    # Trading endpoints will be added here
    # For now, we have basic views in the trading app
    path('pairs/', views.PairConfigListView.as_view(), name='pair_list'),
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('bots/', views.BotSessionListView.as_view(), name='bot_session_list'),
]