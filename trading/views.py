"""
Views for trading app.
"""
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import PairConfig, Order, BotSession
from .serializers import PairConfigSerializer, OrderSerializer, BotSessionSerializer


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