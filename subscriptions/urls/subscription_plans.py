"""
URL configuration for subscription plans endpoints.
"""
from django.urls import path
from subscriptions.api import views as api_views

app_name = 'subscription_plans'

urlpatterns = [
    path('', api_views.SubscriptionPlanListView.as_view(), name='list'),
    path('<int:pk>/', api_views.SubscriptionPlanDetailView.as_view(), name='detail'),
]