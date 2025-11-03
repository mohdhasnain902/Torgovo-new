"""
Django signals for trading app.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Order, BotSession
from subscriptions.utils import update_managed_bot_performance


@receiver(post_save, sender=Order)
def update_performance_on_order(sender, instance, created, **kwargs):
    """
    Update managed bot performance when new order is executed.
    """
    if instance.status == 'executed':
        # Get user's managed bot subscriptions for this pair
        from subscriptions.models import ManagedBotPerformance

        managed_performances = ManagedBotPerformance.objects.filter(
            user=instance.user,
            managed_bot=instance.pair_config
        )

        for performance in managed_performances:
            try:
                update_managed_bot_performance(performance, instance)
            except Exception as e:
                # Log error but don't fail the order processing
                import logging
                logger = logging.getLogger('trading')
                logger.error(f"Error updating managed bot performance: {e}")


@receiver(post_save, sender=Order)
def update_bot_session_on_order(sender, instance, **kwargs):
    """
    Update bot session statistics when order is created or updated.
    """
    if instance.status == 'executed':
        # Find active bot sessions for this user and pair
        active_sessions = BotSession.objects.filter(
            user=instance.user,
            pair_config=instance.pair_config,
            status='running'
        )

        for session in active_sessions:
            # Update order statistics
            session.increment_order_count(success=True)

            # Calculate and update profit/loss for sell orders
            if instance.action == 'sell':
                profit_loss = instance.get_profit_loss()
                session.update_profit_loss(profit_loss)


@receiver(post_save, sender=BotSession)
def log_bot_session_start(sender, instance, created, **kwargs):
    """
    Log when a new bot session is created.
    """
    if created:
        import logging
        logger = logging.getLogger('trading')
        logger.info(f"Bot session started: {instance.session_id} for user {instance.user.username}")


@receiver(post_save, sender=BotSession)
def log_bot_session_status_change(sender, instance, **kwargs):
    """
    Log when bot session status changes.
    """
    if instance.pk:
        try:
            old_instance = BotSession.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                import logging
                logger = logging.getLogger('trading')
                logger.info(
                    f"Bot session {instance.session_id} status changed from "
                    f"{old_instance.status} to {instance.status}"
                )
        except BotSession.DoesNotExist:
            pass  # New instance, already logged above


@receiver(post_delete, sender=Order)
def cleanup_order_data(sender, instance, **kwargs):
    """
    Clean up related data when an order is deleted.
    """
    import logging
    logger = logging.getLogger('trading')
    logger.info(f"Order deleted: {instance.id} for user {instance.user.username}")