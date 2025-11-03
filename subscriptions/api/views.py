"""
API views for subscriptions app.
"""
from rest_framework import generics, status, views, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, F, Q, Count
from django.http import JsonResponse
from decimal import Decimal
import logging

from ..models import (
    SubscriptionPlan, UserSubscription, CustomBotWebhook,
    ManagedBotPerformance
)
from .serializers import (
    SubscriptionPlanSerializer, UserSubscriptionSerializer,
    CustomBotWebhookSerializer, CustomBotWebhookCreateSerializer,
    ManagedBotPerformanceSerializer, ManagedBotPerformanceCreateSerializer,
    WebhookPayloadSerializer, SubscriptionUsageSerializer,
    PerformanceSummarySerializer, ManagedBotRankingSerializer
)
from .serializers_additional import (
    UserSubscriptionCreateSerializer, UserSubscriptionUpdateSerializer
)
from ..utils import (
    validate_webhook_request, log_webhook_request,
    validate_webhook_payload, check_subscription_limits,
    calculate_managed_bot_performance, get_performance_summary,
    get_managed_bot_rankings
)
from trading.bot_manager import trading_manager

# Configure logging
webhook_logger = logging.getLogger('webhooks')
api_logger = logging.getLogger('api')


class SubscriptionPlanListView(generics.ListAPIView):
    """List all active subscription plans."""
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]  # Public pricing

    def get_queryset(self):
        """Filter by plan_type if provided."""
        queryset = SubscriptionPlan.objects.filter(
            is_active=True,
            is_public=True
        ).order_by('sort_order', 'monthly_price')

        plan_type = self.request.query_params.get('plan_type')
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)

        return queryset


class SubscriptionPlanDetailView(generics.RetrieveAPIView):
    """Get details of a specific subscription plan."""
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    queryset = SubscriptionPlan.objects.filter(
        is_active=True,
        is_public=True
    )


class UserSubscriptionListView(generics.ListCreateAPIView):
    """List user's subscriptions or create new subscription."""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get current user's subscriptions."""
        return UserSubscription.objects.filter(
            user=self.request.user
        ).select_related('plan', 'user')

    def get_serializer_class(self):
        """Use different serializer for creation."""
        if self.request.method == 'POST':
            return UserSubscriptionCreateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        """Create new subscription."""
        user = self.request.user
        plan = serializer.validated_data['plan_id']

        # Check if user already has active subscription for this plan type
        existing_subscription = UserSubscription.objects.filter(
            user=user,
            plan__plan_type=plan.plan_type,
            status__in=['active', 'trial'],
            end_date__gte=timezone.now()
        ).first()

        if existing_subscription:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You already have an active subscription for this plan type")

        # Check if user has reached maximum subscriptions
        active_subscriptions = UserSubscription.objects.filter(
            user=user,
            status='active',
            end_date__gte=timezone.now()
        ).count()

        if active_subscriptions >= 5:  # Maximum 5 active subscriptions
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You have reached the maximum number of active subscriptions")

        # Create subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=7),  # 7-day trial
            trial_end_date=timezone.now() + timezone.timedelta(days=7),
            status='trial',
            billing_cycle=serializer.validated_data.get('billing_cycle', 'monthly'),
            auto_renew=serializer.validated_data.get('auto_renew', False),
            payment_method=serializer.validated_data.get('payment_method')
        )

        return subscription


class UserSubscriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or cancel a specific subscription."""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get current user's subscriptions."""
        return UserSubscription.objects.filter(
            user=self.request.user
        ).select_related('plan', 'user')

    def perform_update(self, serializer):
        """Update subscription with validation."""
        instance = self.get_instance()

        # Validate status changes
        new_status = serializer.validated_data.get('status')
        if new_status == 'cancelled':
            instance.cancel_subscription(immediate=True)
        elif new_status:
            instance.status = new_status
            instance.save()

    def get_serializer_class(self):
        """Use different serializer for updates."""
        if self.request.method in ['PUT', 'PATCH']:
            return UserSubscriptionUpdateSerializer
        return super().get_serializer_class()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_subscription(request):
    """Get current user's active subscription with plan details."""
    subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gte=timezone.now()
    ).select_related('plan').first()

    if not subscription:
        return Response({
            'message': 'No active subscription found',
            'subscription': None
        }, status=200)

    serializer = UserSubscriptionSerializer(subscription)
    return Response(serializer.data)


class CustomBotWebhookCreateView(generics.CreateAPIView):
    """Generate webhook URL and TradingView config for user."""
    serializer_class = CustomBotWebhookCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Create webhook with validation."""
        user = self.request.user

        # Check subscription limits
        can_use, subscription, message = check_subscription_limits(user, 'custom_bot_webhooks')
        if not can_use:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(message)

        webhook = serializer.save()

        # Log webhook creation
        api_logger.info(f"Created webhook for user {user.id}: {webhook.webhook_name}")

        return webhook

    def create(self, request, *args, **kwargs):
        """Create webhook and return full configuration."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        webhook = self.perform_create(serializer)

        # Return webhook details with TradingView config
        response_serializer = CustomBotWebhookSerializer(webhook)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CustomBotWebhookListView(generics.ListAPIView):
    """List user's custom bot webhooks."""
    serializer_class = CustomBotWebhookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get current user's webhooks."""
        return CustomBotWebhook.objects.filter(
            user=self.request.user
        ).select_related('pair_config', 'subscription')


class CustomBotWebhookDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific webhook."""
    serializer_class = CustomBotWebhookSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get current user's webhooks."""
        return CustomBotWebhook.objects.filter(
            user=self.request.user
        ).select_related('pair_config', 'subscription')


class TradingViewWebhookView(views.APIView):
    """Receive TradingView webhook alerts and execute trades."""
    permission_classes = [permissions.AllowAny]  # Auth handled via webhook secret

    def post(self, request, webhook_secret):
        """Process TradingView webhook payload."""
        start_time = timezone.now()

        try:
            # Validate webhook request
            is_valid, webhook, error_message = validate_webhook_request(
                request, webhook_secret
            )

            if not is_valid:
                log_webhook_request(request, webhook_secret, 401, webhook)
                return Response({
                    'error': 'Unauthorized',
                    'message': error_message
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Validate payload
            payload_serializer = WebhookPayloadSerializer(data=request.data)
            if not payload_serializer.is_valid():
                log_webhook_request(request, webhook_secret, 400, webhook)
                return Response({
                    'error': 'Invalid payload',
                    'message': payload_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            payload = payload_serializer.validated_data

            # Execute trade
            result = self._execute_trade(webhook, payload)

            # Record webhook trigger
            webhook.record_trigger(
                success=result['success'],
                ip_address=self._get_client_ip(request)
            )

            processing_time = (timezone.now() - start_time).total_seconds()
            response_data = {
                'status': 'success' if result['success'] else 'error',
                'message': result.get('message', 'Trade executed successfully'),
                'order_id': result.get('order_id'),
                'processing_time_ms': round(processing_time * 1000, 2)
            }

            status_code = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
            log_webhook_request(request, webhook_secret, status_code, webhook)

            return Response(response_data, status=status_code)

        except Exception as e:
            webhook_logger.error(f"Error processing webhook: {e}", exc_info=True)
            log_webhook_request(request, webhook_secret, 500)

            return Response({
                'status': 'error',
                'message': 'Internal server error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _execute_trade(self, webhook, payload):
        """Execute trade based on webhook payload."""
        try:
            user = webhook.user
            pair_config = webhook.pair_config
            action = payload['action']
            quantity = Decimal(str(payload['quantity']))
            price = Decimal(str(payload.get('price', 0))) if payload.get('price') else None

            # Execute trade through TradingManager
            order = trading_manager.execute_webhook_order(
                user=user,
                pair_config=pair_config,
                action=action,
                quantity=quantity,
                price=price,
                webhook_secret=webhook.webhook_secret
            )

            return {
                'success': True,
                'message': f"{action.upper()} order executed successfully",
                'order_id': str(order.id),
                'order_details': {
                    'action': order.action,
                    'pair': order.pair_config.pair_symbol,
                    'quantity': str(order.quantity),
                    'price': str(order.price),
                    'executed_price': str(order.executed_price) if order.executed_price else None
                }
            }

        except Exception as e:
            webhook_logger.error(f"Error executing trade: {e}", exc_info=True)
            return {
                'success': False,
                'message': f"Failed to execute trade: {str(e)}"
            }

    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def webhook_test(request, webhook_secret):
    """Test webhook connectivity without executing trades."""
    try:
        webhook = CustomBotWebhook.objects.get(
            webhook_secret=webhook_secret,
            user=request.user
        )

        return Response({
            'status': 'success',
            'webhook': {
                'id': webhook.id,
                'name': webhook.webhook_name,
                'pair_config': {
                    'symbol': webhook.pair_config.pair_symbol,
                    'exchange': webhook.pair_config.exchange
                },
                'is_active': webhook.is_active,
                'total_triggers': webhook.total_triggers,
                'successful_triggers': webhook.successful_triggers,
                'last_triggered': webhook.last_triggered
            }
        })

    except CustomBotWebhook.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Webhook not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def available_managed_bots(request):
    """List available managed bots with performance stats."""
    exchange = request.query_params.get('exchange')
    pair = request.query_params.get('pair')
    strategy = request.query_params.get('strategy')

    # Get active managed bot pair configurations
    queryset = SubscriptionPlan.objects.filter(
        plan_type='managed_bot',
        is_active=True
    )

    # This is simplified - in production, you'd get actual managed bot pairs
    managed_bots = [
        {
            'id': 1,
            'name': 'BTC Momentum Bot',
            'pair_symbol': 'BTCUSDT',
            'exchange': 'binance',
            'strategy_type': 'momentum',
            'description': 'High-frequency BTC trading using momentum indicators',
            'performance_30d': '15.5',
            'performance_90d': '45.2',
            'total_subscribers': 125,
            'min_investment': '1000.00',
            'profit_share_percentage': '25.0',
            'guaranteed_monthly_return': '5.0'
        },
        {
            'id': 2,
            'name': 'ETH Trend Following',
            'pair_symbol': 'ETHUSDT',
            'exchange': 'bybit',
            'strategy_type': 'trend_following',
            'description': 'ETH trend following with risk management',
            'performance_30d': '12.3',
            'performance_90d': '38.7',
            'total_subscribers': 89,
            'min_investment': '500.00',
            'profit_share_percentage': '30.0',
            'guaranteed_monthly_return': '7.0'
        }
    ]

    # Apply filters
    if exchange:
        managed_bots = [bot for bot in managed_bots if bot['exchange'] == exchange]
    if pair:
        managed_bots = [bot for bot in managed_bots if bot['pair_symbol'] == pair]
    if strategy:
        managed_bots = [bot for bot in managed_bots if bot['strategy_type'] == strategy]

    return Response({
        'count': len(managed_bots),
        'results': managed_bots
    })


class ManagedBotSubscribeView(generics.CreateAPIView):
    """Subscribe to a managed bot with investment amount."""
    serializer_class = ManagedBotPerformanceCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Create managed bot subscription with validation."""
        user = self.request.user

        # Check if user has active managed bot subscription
        active_subscription = UserSubscription.objects.filter(
            user=user,
            status='active',
            end_date__gte=timezone.now(),
            plan__plan_type='managed_bot'
        ).first()

        if not active_subscription:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Active managed bot subscription required")

        # Check investment limits
        initial_investment = serializer.validated_data['initial_investment']
        min_investment = active_subscription.plan.min_investment

        if min_investment and initial_investment < min_investment:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Minimum investment is {min_investment} USDT"
            )

        return serializer.save()

    def create(self, request, *args, **kwargs):
        """Create managed bot subscription."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        performance = self.perform_create(serializer)

        # Start the managed bot
        try:
            session_id = trading_manager.start_bot(
                user=request.user,
                pair_config=performance.managed_bot,
                session_config={'type': 'managed_bot'}
            )

            response_serializer = ManagedBotPerformanceSerializer(performance)
            return Response({
                'performance': response_serializer.data,
                'session_id': session_id,
                'message': 'Successfully subscribed to managed bot'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            api_logger.error(f"Failed to start managed bot: {e}")
            return Response({
                'error': 'Failed to start managed bot',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def managed_bot_performance(request):
    """Get user's managed bot performance and P&L."""
    user = request.user
    period_days = int(request.query_params.get('period_days', 30))
    bot_id = request.query_params.get('bot_id')

    # Get performance records
    queryset = ManagedBotPerformance.objects.filter(user=user)

    if bot_id:
        queryset = queryset.filter(managed_bot_id=bot_id)

    performances = queryset.select_related('managed_bot', 'subscription')

    if not performances.exists():
        return Response({
            'message': 'No managed bot performance data found',
            'performance_data': None
        }, status=200)

    # Calculate summary
    summary = get_performance_summary(user, period_days)

    # Get individual bot performances
    bot_performances = []
    for perf in performances:
        serializer = ManagedBotPerformanceSerializer(perf)
        bot_data = serializer.data
        bot_performances.append(bot_data)

    return Response({
        'summary': PerformanceSummarySerializer(summary).data,
        'bots': bot_performances,
        'period_days': period_days
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def subscription_usage(request):
    """Get current subscription usage statistics."""
    user = request.user

    # Get active subscription
    subscription = UserSubscription.objects.filter(
        user=user,
        status='active',
        end_date__gte=timezone.now()
    ).select_related('plan').first()

    if not subscription:
        return Response({
            'message': 'No active subscription found',
            'usage': None
        }, status=200)

    # Calculate usage statistics
    usage_stats = {
        'api_calls_used': subscription.api_calls_used_today,
        'api_calls_limit': subscription.plan.api_calls_per_day,
        'api_calls_remaining': max(0, subscription.plan.api_calls_per_day - subscription.api_calls_used_today),
        'webhook_requests_used': subscription.webhook_requests_used_hour,
        'webhook_requests_limit': subscription.plan.webhook_requests_per_hour,
        'webhook_requests_remaining': max(0, subscription.plan.webhook_requests_per_hour - subscription.webhook_requests_used_hour),
        'bots_used': CustomBotWebhook.objects.filter(user=user, is_active=True).count(),
        'bots_limit': subscription.plan.max_bots or 1,
        'pairs_used': CustomBotWebhook.objects.filter(user=user, is_active=True).values('pair_config').distinct().count(),
        'pairs_limit': subscription.plan.max_trading_pairs or 1
    }

    serializer = SubscriptionUsageSerializer(usage_stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def managed_bot_rankings(request):
    """Get ranked list of managed bots by performance."""
    period_days = int(request.query_params.get('period_days', 30))

    try:
        rankings = get_managed_bot_rankings(period_days)
        serializer = ManagedBotRankingSerializer(rankings, many=True)

        return Response({
            'period_days': period_days,
            'rankings': serializer.data
        })

    except Exception as e:
        api_logger.error(f"Error getting managed bot rankings: {e}")
        return Response({
            'error': 'Failed to get rankings',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_subscription(request, subscription_id):
    """Cancel a subscription immediately."""
    try:
        subscription = UserSubscription.objects.get(
            id=subscription_id,
            user=request.user
        )

        subscription.cancel_subscription(immediate=True)

        # Stop related bots
        related_webhooks = CustomBotWebhook.objects.filter(
            subscription=subscription,
            is_active=True
        )

        for webhook in related_webhooks:
            webhook.is_active = False
            webhook.save()

            # Stop bot sessions
            trading_manager.stop_bot(
                user=request.user,
                pair_symbol=webhook.pair_config.pair_symbol,
                exchange=webhook.pair_config.exchange
            )

        return Response({
            'message': 'Subscription cancelled successfully',
            'cancellation_date': timezone.now()
        })

    except UserSubscription.DoesNotExist:
        return Response({
            'error': 'Subscription not found'
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        api_logger.error(f"Error cancelling subscription: {e}")
        return Response({
            'error': 'Failed to cancel subscription',
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)