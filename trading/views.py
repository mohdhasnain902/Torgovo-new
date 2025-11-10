"""
Trading API views for managing trading bots and operations.
"""
import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Order, BotSession, PairConfig
from .serializers import PairConfigSerializer, OrderSerializer, BotSessionSerializer
from .bot_manager import trading_manager
from subscriptions.models import UserSubscription

logger = logging.getLogger('trading')


class TradingPagination(PageNumberPagination):
    """Custom pagination for trading endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PairConfigListView(generics.ListAPIView):
    """List available trading pair configurations."""
    serializer_class = PairConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = PairConfig.objects.filter(is_active=True)

        # Filter by exchange if provided
        exchange = self.request.query_params.get('exchange')
        if exchange:
            queryset = queryset.filter(exchange=exchange)

        # Filter by bot type if provided
        bot_type = self.request.query_params.get('bot_type')
        if bot_type:
            queryset = queryset.filter(bot_type=bot_type)

        return queryset


class OrderListView(generics.ListAPIView):
    """List user's orders."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).select_related('pair_config').order_by('-created_at')


class BotSessionListView(generics.ListAPIView):
    """List user's bot sessions."""
    serializer_class = BotSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BotSession.objects.filter(
            user=self.request.user
        ).select_related('pair_config').order_by('-started_at')


@method_decorator(csrf_exempt, name='dispatch')
class TradingBotView(APIView):
    """
    View for managing trading bots.

    Handles starting, stopping, and managing trading bot sessions.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Start a new trading bot session.

        Expected payload:
        {
            "pair_config_id": 1,
            "exchange": "binance",  # optional, overrides pair_config.exchange
            "session_config": {}     # optional additional configuration
        }
        """
        try:
            pair_config_id = request.data.get('pair_config_id')
            exchange = request.data.get('exchange')
            session_config = request.data.get('session_config', {})

            if not pair_config_id:
                return Response(
                    {'error': 'pair_config_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get pair configuration
            pair_config = get_object_or_404(PairConfig, id=pair_config_id, user=request.user)

            # Check if user has active subscription
            try:
                user_sub = UserSubscription.objects.get(user=request.user, is_active=True)
                if not user_sub.can_create_custom_bot():
                    return Response(
                        {'error': 'Subscription limit reached or plan does not allow custom bots'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except UserSubscription.DoesNotExist:
                return Response(
                    {'error': 'Active subscription required'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Start bot session
            session_id = trading_manager.start_bot(
                user=request.user,
                pair_config=pair_config,
                exchange=exchange,
                session_config=session_config
            )

            return Response({
                'success': True,
                'session_id': session_id,
                'message': 'Trading bot started successfully'
            })

        except Exception as e:
            logger.error(f"Error starting trading bot: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """
        Stop a trading bot session.

        Expected query parameters:
        - session_id: Specific session ID to stop (optional)
        - pair_symbol: Trading pair symbol (required if session_id not provided)
        - exchange: Exchange name (required if session_id not provided)
        """
        try:
            session_id = request.query_params.get('session_id')
            pair_symbol = request.query_params.get('pair_symbol')
            exchange = request.query_params.get('exchange')

            if session_id:
                # Stop specific session
                trading_manager.stop_bot(
                    user=request.user,
                    pair_symbol=None,
                    exchange=None,
                    session_id=session_id
                )
            elif pair_symbol and exchange:
                # Stop all bots for this pair and exchange
                trading_manager.stop_bot(
                    user=request.user,
                    pair_symbol=pair_symbol,
                    exchange=exchange
                )
            else:
                return Response(
                    {'error': 'Either session_id or both pair_symbol and exchange required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                'success': True,
                'message': 'Trading bot stopped successfully'
            })

        except Exception as e:
            logger.error(f"Error stopping trading bot: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """
        Get active trading bot sessions.

        Returns paginated list of active bot sessions for the user.
        """
        try:
            sessions = trading_manager.get_active_sessions(user=request.user)

            # Apply pagination
            paginator = TradingPagination()
            page = paginator.paginate_queryset(sessions, request)

            # Serialize sessions
            session_data = []
            for session in page:
                session_data.append({
                    'session_id': session.session_id,
                    'bot_type': session.bot_type,
                    'status': session.status,
                    'pair_symbol': session.pair_config.pair_symbol,
                    'exchange': session.pair_config.exchange,
                    'started_at': session.started_at,
                    'stopped_at': session.stopped_at,
                    'successful_orders': session.successful_orders,
                    'failed_orders': session.failed_orders,
                    'total_profit_loss': str(session.total_profit_loss),
                    'session_config': session.session_config
                })

            return paginator.get_paginated_response({
                'success': True,
                'sessions': session_data
            })

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ArbitrageBotView(APIView):
    """
    View for managing arbitrage trading bots.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Start an arbitrage bot.

        Expected payload:
        {
            "exchange": "bybit",
            "session_config": {}  # optional additional configuration
        }
        """
        try:
            exchange = request.data.get('exchange')
            session_config = request.data.get('session_config', {})

            if not exchange:
                return Response(
                    {'error': 'exchange is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if user has active subscription
            try:
                user_sub = UserSubscription.objects.get(user=request.user, is_active=True)
                # Note: Arbitrage bots might need different subscription checks
            except UserSubscription.DoesNotExist:
                return Response(
                    {'error': 'Active subscription required'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Start arbitrage bot
            session_id = trading_manager.start_arbitrage_bot(
                user=request.user,
                exchange=exchange,
                session_config=session_config
            )

            if session_id:
                return Response({
                    'success': True,
                    'session_id': session_id,
                    'message': 'Arbitrage bot started successfully'
                })
            else:
                return Response(
                    {'error': 'Failed to start arbitrage bot'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Error starting arbitrage bot: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        """
        Stop an arbitrage bot.

        Expected query parameters:
        - exchange: Exchange name
        """
        try:
            exchange = request.query_params.get('exchange')

            if not exchange:
                return Response(
                    {'error': 'exchange is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            success = trading_manager.stop_arbitrage_bot(
                user=request.user,
                exchange=exchange
            )

            if success:
                return Response({
                    'success': True,
                    'message': 'Arbitrage bot stopped successfully'
                })
            else:
                return Response(
                    {'error': 'Arbitrage bot not found or already stopped'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            logger.error(f"Error stopping arbitrage bot: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def trading_statistics(request):
    """
    Get trading statistics for the user.

    Returns comprehensive trading statistics including:
    - Total sessions
    - Active sessions
    - Order statistics
    - Profit/loss data
    """
    try:
        stats = trading_manager.get_bot_statistics(user=request.user)

        # Get additional detailed statistics
        user_orders = Order.objects.filter(user=request.user)
        user_sessions = BotSession.objects.filter(user=request.user)

        detailed_stats = {
            **stats,
            'orders_by_status': {
                'pending': user_orders.filter(status='pending').count(),
                'executed': user_orders.filter(status='executed').count(),
                'cancelled': user_orders.filter(status='cancelled').count(),
                'failed': user_orders.filter(status='failed').count(),
            },
            'orders_by_action': {
                'buy': user_orders.filter(action='buy').count(),
                'sell': user_orders.filter(action='sell').count(),
            },
            'recent_orders': [
                {
                    'id': order.id,
                    'action': order.action,
                    'pair_symbol': order.pair_config.pair_symbol,
                    'exchange': order.pair_config.exchange,
                    'quantity': str(order.quantity),
                    'price': str(order.price),
                    'status': order.status,
                    'created_at': order.created_at,
                    'executed_at': order.executed_at,
                }
                for order in user_orders.select_related('pair_config').order_by('-created_at')[:10]
            ],
            'active_bots': [
                {
                    'session_id': session.session_id,
                    'bot_type': session.bot_type,
                    'pair_symbol': session.pair_config.pair_symbol,
                    'exchange': session.pair_config.exchange,
                    'started_at': session.started_at,
                }
                for session in user_sessions.filter(status='running').select_related('pair_config')
            ]
        }

        return Response({
            'success': True,
            'statistics': detailed_stats
        })

    except Exception as e:
        logger.error(f"Error getting trading statistics: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def bot_session_detail(request, session_id):
    """
    Get detailed information about a specific bot session.

    Parameters:
    - session_id: Bot session ID
    """
    try:
        session = get_object_or_404(
            BotSession,
            session_id=session_id,
            user=request.user
        )

        # Get related orders for this session
        orders = Order.objects.filter(
            user=request.user,
            pair_config=session.pair_config,
            created_at__gte=session.started_at,
            created_at__lte=session.stopped_at or timezone.now()
        ).select_related('pair_config').order_by('-created_at')

        session_data = {
            'session_id': session.session_id,
            'bot_type': session.bot_type,
            'status': session.status,
            'pair_symbol': session.pair_config.pair_symbol,
            'exchange': session.pair_config.exchange,
            'started_at': session.started_at,
            'stopped_at': session.stopped_at,
            'successful_orders': session.successful_orders,
            'failed_orders': session.failed_orders,
            'total_profit_loss': str(session.total_profit_loss),
            'session_config': session.session_config,
            'orders': [
                {
                    'id': order.id,
                    'action': order.action,
                    'order_type': order.order_type,
                    'quantity': str(order.quantity),
                    'price': str(order.price),
                    'executed_price': str(order.executed_price) if order.executed_price else None,
                    'executed_quantity': str(order.executed_quantity) if order.executed_quantity else None,
                    'status': order.status,
                    'source': order.source,
                    'created_at': order.created_at,
                    'executed_at': order.executed_at,
                }
                for order in orders
            ]
        }

        return Response({
            'success': True,
            'session': session_data
        })

    except Exception as e:
        logger.error(f"Error getting bot session detail: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_http_methods(["POST"])
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Webhook is called by TradingView
def trading_webhook(request):
    """
    TradingView webhook endpoint for executing trades.

    Expected payload:
    {
        "webhook_secret": "user_webhook_secret",
        "pair_symbol": "BTCUSDT",
        "action": "buy",  # or "sell"
        "quantity": "0.001",
        "price": "50000"  # optional, for limit orders
    }
    """
    try:
        data = request.data

        # Validate required fields
        webhook_secret = data.get('webhook_secret')
        pair_symbol = data.get('pair_symbol')
        action = data.get('action')
        quantity = data.get('quantity')

        if not all([webhook_secret, pair_symbol, action, quantity]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: webhook_secret, pair_symbol, action, quantity'
            }, status=400)

        if action not in ['buy', 'sell']:
            return JsonResponse({
                'success': False,
                'error': 'Action must be either "buy" or "sell"'
            }, status=400)

        # Find user subscription by webhook secret
        try:
            user_sub = UserSubscription.objects.select_related('user').get(
                webhook_secret=webhook_secret,
                is_active=True
            )
            user = user_sub.user
        except UserSubscription.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Invalid or inactive webhook secret'
            }, status=401)

        # Find pair configuration
        try:
            pair_config = PairConfig.objects.get(
                user=user,
                pair_symbol=pair_symbol.upper(),
                is_active=True
            )
        except PairConfig.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'No active pair configuration found for {pair_symbol}'
            }, status=404)

        # Convert quantity and price to Decimal
        try:
            quantity = Decimal(str(quantity))
            price = Decimal(str(data['price'])) if data.get('price') else None
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid quantity or price format'
            }, status=400)

        # Execute order through trading manager
        order = trading_manager.execute_webhook_order(
            user=user,
            pair_config=pair_config,
            action=action,
            quantity=quantity,
            price=price,
            webhook_secret=webhook_secret
        )

        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'action': order.action,
            'pair_symbol': order.pair_config.pair_symbol,
            'quantity': str(order.quantity),
            'price': str(order.price),
            'status': order.status,
            'message': f'{action.title()} order placed successfully'
        })

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


# For direct Django view (non-DRF) compatibility
trading_webhook_django = trading_webhook