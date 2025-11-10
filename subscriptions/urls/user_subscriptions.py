"""
URL configuration for user subscriptions endpoints.
"""
from django.urls import path
from subscriptions.api import views as api_views

app_name = 'user_subscriptions'

urlpatterns = [
    path('', views.UserSubscriptionListView.as_view(), name='list'),
    path('<int:pk>/', views.UserSubscriptionDetailView.as_view(), name='detail'),
    path('my-subscription/', views.my_subscription, name='my_subscription'),
    path('usage/', views.subscription_usage, name='usage'),
    path('<int:subscription_id>/cancel/', views.cancel_subscription, name='cancel'),
]