"""Orders signals."""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Order, OrderItem, VendorEarnings


@receiver(post_save, sender=OrderItem)
def create_vendor_earnings(sender, instance, created, **kwargs):
    """Create vendor earnings when order item is created."""
    if created:
        # This is handled in the order creation view to avoid duplicates
        pass


@receiver(pre_delete, sender=OrderItem)
def restore_inventory_on_delete(sender, instance, **kwargs):
    """Restore inventory when order item is deleted."""
    if instance.order.status in ['PENDING', 'CANCELLED']:
        instance.product.inventory += instance.quantity
        instance.product.save(update_fields=['inventory'])