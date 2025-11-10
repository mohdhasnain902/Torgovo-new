"""
URL configuration for user subscriptions endpoints.
"""
from django.urls import path
from subscriptions.api import views as api_views

app_name = 'user_subscriptions'

urlpatterns = [
    path('', api_views.UserSubscriptionListView.as_view(), name='list'),
    path('<int:pk>/', api_views.UserSubscriptionDetailView.as_view(), name='detail'),
    path('my-subscription/', api_views.my_subscription, name='my_subscription'),
    path('usage/', api_views.subscription_usage, name='usage'),
    path('<int:subscription_id>/cancel/', api_views.cancel_subscription, name='cancel'),
]