"""Common utility functions."""

import uuid
import os
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage


def generate_unique_filename(instance, filename):
    """Generate a unique filename for uploaded files."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return filename


def validate_file_size(file, max_size_mb=10):
    """Validate file size."""
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'File size cannot exceed {max_size_mb}MB.')


def validate_image_file(file):
    """Validate image file type and size."""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in valid_extensions:
        raise ValidationError('Only JPG, PNG, and WebP images are allowed.')

    validate_file_size(file, max_size_mb=5)


def validate_audio_file(file):
    """Validate audio file type and size."""
    valid_extensions = ['.mp3', '.wav', '.ogg', '.m4a']
    ext = os.path.splitext(file.name)[1].lower()

    if ext not in valid_extensions:
        raise ValidationError(
            'Only MP3, WAV, OGG, and M4A audio files are allowed.')

    validate_file_size(file, max_size_mb=50)


def calculate_discounted_price(price, discount_percentage):
    """Calculate discounted price."""
    if discount_percentage and 0 < discount_percentage < 100:
        discount_amount = price * (Decimal(discount_percentage) / 100)
        return price - discount_amount
    return price


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def create_signed_url(file_path, expiry_seconds=3600):
    """Create a signed URL for file access."""
    # This is a placeholder implementation
    # In production, you would use your storage backend's signed URL feature
    if hasattr(default_storage, 'url'):
        return default_storage.url(file_path)
    return None


class Constants:
    """Application constants."""

    # User Roles
    ADMIN = 'ADMIN'
    VENDOR = 'VENDOR'
    CUSTOMER = 'CUSTOMER'

    USER_ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (VENDOR, 'Vendor'),
        (CUSTOMER, 'Customer'),
    ]

    # Product Categories
    BOOKS = 'BOOKS'
    TOYS = 'TOYS'

    CATEGORY_TYPE_CHOICES = [
        (BOOKS, 'Books'),
        (TOYS, 'Toys'),
    ]

    # Order Status
    PENDING = 'PENDING'
    PAID = 'PAID'
    SHIPPED = 'SHIPPED'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'

    ORDER_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]

    # Age Ranges
    AGE_RANGES = [
        (0, 2, '0-2 years'),
        (3, 5, '3-5 years'),
        (6, 8, '6-8 years'),
        (9, 12, '9-12 years'),
        (13, 17, '13-17 years'),
    ]
