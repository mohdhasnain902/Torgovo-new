"""
URL configuration for subscription plans endpoints.
"""
from django.urls import path
from . import views

app_name = 'subscription_plans'

urlpatterns = [
    path('', views.SubscriptionPlanListView.as_view(), name='list'),
    path('<int:pk>/', views.SubscriptionPlanDetailView.as_view(), name='detail'),
]