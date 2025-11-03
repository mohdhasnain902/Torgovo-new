"""
Additional serializers for subscriptions app.
"""
from rest_framework import serializers
from django.utils import timezone
from ..models import UserSubscription


class UserSubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new subscriptions."""
    plan_id = serializers.IntegerField(write_only=True)
    billing_cycle = serializers.ChoiceField(
        choices=UserSubscription.BILLING_CYCLE_CHOICES,
        default='monthly'
    )
    auto_renew = serializers.BooleanField(default=False)
    payment_method = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True
    )

    class Meta:
        model = UserSubscription
        fields = [
            'plan_id', 'billing_cycle', 'auto_renew', 'payment_method'
        ]

    def validate_plan_id(self, value):
        """Validate plan ID."""
        try:
            from ..models import SubscriptionPlan
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return plan
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan")

    def create(self, validated_data):
        """Create subscription with trial period."""
        plan = validated_data.pop('plan_id')
        user = self.context['request'].user

        # Create 7-day trial subscription
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            status='trial',
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=7),
            trial_end_date=timezone.now() + timezone.timedelta(days=7),
            **validated_data
        )

        return subscription


class UserSubscriptionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating subscriptions."""
    status = serializers.ChoiceField(
        choices=UserSubscription.STATUS_CHOICES,
        required=False
    )
    auto_renew = serializers.BooleanField(required=False)

    class Meta:
        model = UserSubscription
        fields = [
            'status', 'auto_renew', 'notes'
        ]