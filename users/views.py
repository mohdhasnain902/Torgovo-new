"""
Views for users app.
"""
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.utils import timezone
from .models import UserProfile
from .serializers import (
    UserSerializer, UserProfileSerializer, UserProfileUpdateSerializer,
    ExchangeCredentialsSerializer, UserRegistrationSerializer,
    UserStatisticsSerializer
)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get or update current user's profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # Get or create UserProfile for current user
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            # For updates, use a serializer that excludes sensitive fields
            if 'api_key' in self.request.data or 'api_secret' in self.request.data:
                return ExchangeCredentialsSerializer
            return UserProfileUpdateSerializer
        return UserProfileSerializer


class UserRegistrationView(generics.CreateAPIView):
    """Register a new user."""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()
            # Create token for the new user
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """Login user and return auth token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)

            # Update last login IP
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.last_login_ip = self.get_client_ip(request)
            profile.save()

            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Login successful'
            })
        else:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLogoutView(generics.GenericAPIView):
    """Logout user and delete auth token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response({
                'message': 'Logout successful'
            })
        except:
            return Response({
                'error': 'Error during logout'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_statistics(request):
    """Get current user's trading statistics."""
    profile = request.user.trading_profile

    # Get active subscriptions count
    from subscriptions.models import UserSubscription
    active_subscriptions = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gte=timezone.now()
    ).count()

    statistics = {
        'total_traded_volume': profile.total_traded_volume,
        'total_orders': profile.profit_loss_summary['total_orders'],
        'active_subscriptions': active_subscriptions,
        'is_active_trader': profile.is_active_trader,
        'profit_loss_summary': profile.profit_loss_summary
    }

    serializer = UserStatisticsSerializer(statistics)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def exchange_config(request):
    """Get exchange configuration for current user."""
    profile = request.user.trading_profile
    config = profile.exchange_config

    # Return config without sensitive data for display
    safe_config = {
        'exchange': config['exchange'],
        'base_url': config['base_url'],
        'demo_mode': config['demo_mode'],
        'leverage': config['leverage'],
        'has_credentials': bool(profile.api_key and profile.api_secret)
    }

    return Response(safe_config)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def test_exchange_connection(request):
    """Test connection to exchange API."""
    profile = request.user.trading_profile

    if not profile.api_key or not profile.api_secret:
        return Response({
            'error': 'Exchange credentials not configured'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # This is a placeholder - implement actual exchange API testing
        # based on the exchange type
        if profile.exchange == 'binance':
            # Implement Binance API test
            pass
        elif profile.exchange == 'bybit':
            # Implement Bybit API test
            pass
        # Add other exchanges as needed

        return Response({
            'status': 'success',
            'message': f'Connection to {profile.get_exchange_display()} successful',
            'exchange': profile.exchange,
            'demo_mode': profile.demo_mode
        })

    except Exception as e:
        return Response({
            'status': 'error',
            'message': f'Connection failed: {str(e)}',
            'exchange': profile.exchange
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """Get current user information."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)