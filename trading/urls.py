"""
URL configuration for trading app.
"""
from django.urls import path
from . import views

app_name = 'trading'

urlpatterns = [
    # Basic trading data endpoints
    path('pairs/', views.PairConfigListView.as_view(), name='pair_list'),
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('sessions/', views.BotSessionListView.as_view(), name='bot_session_list'),

    # Trading bot management endpoints
    path('bots/manage/', views.TradingBotView.as_view(), name='trading_bot_manage'),
    path('bots/arbitrage/', views.ArbitrageBotView.as_view(), name='arbitrage_bot_manage'),
    path('statistics/', views.trading_statistics, name='trading_statistics'),
    path('sessions/<str:session_id>/', views.bot_session_detail, name='bot_session_detail'),

    # TradingView webhook endpoint
    path('webhook/', views.trading_webhook, name='trading_webhook'),
]