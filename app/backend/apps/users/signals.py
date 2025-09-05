"""User signals."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, CustomerProfile


@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    """Create customer profile when a new customer user is created."""
    if created and instance.role == 'CUSTOMER':
        CustomerProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    """Save customer profile when user is saved."""
    if instance.role == 'CUSTOMER' and hasattr(instance, 'customer_profile'):
        instance.customer_profile.save()