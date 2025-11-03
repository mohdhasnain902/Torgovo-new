"""
URL configuration for users app.
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('current/', views.current_user, name='current_user'),

    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('statistics/', views.user_statistics, name='statistics'),
    path('exchange-config/', views.exchange_config, name='exchange_config'),
    path('test-connection/', views.test_exchange_connection, name='test_connection'),
]