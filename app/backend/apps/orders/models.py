"""Orders models."""

from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.common.models import BaseModel
from apps.common.utils import Constants
from apps.catalog.models import Product

User = get_user_model()


class Cart(BaseModel):
    """Shopping cart model."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Anonymous Cart ({self.session_key})"

    @property
    def total_items(self):
        """Get total number of items in cart."""
        return self.items.aggregate(  # type: ignore
            total=models.Sum('quantity')
        )['total'] or 0

    @property
    def subtotal(self):
        """Calculate cart subtotal."""
        total = Decimal('0.00')
        for item in self.items.all():  # type: ignore
            total += item.total_price
        return total

    @property
    def total_savings(self):
        """Calculate total savings from sales."""
        savings = Decimal('0.00')
        for item in self.items.all():  # type: ignore
            if item.product.is_on_sale:
                original_price = item.product.price * item.quantity
                sale_price = item.product.current_price * item.quantity
                savings += original_price - sale_price
        return savings


class CartItem(BaseModel):
    """Cart item model."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.title}"

    @property
    def unit_price(self):
        """Get unit price (current price)."""
        return self.product.current_price

    @property
    def total_price(self):
        """Calculate total price for this item."""
        return self.unit_price * self.quantity


class Order(BaseModel):
    """Order model."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Constants.ORDER_STATUS_CHOICES,
        default=Constants.PENDING
    )

    # Totals
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Addresses (stored as JSON to preserve historical data)
    shipping_address = models.JSONField()
    billing_address = models.JSONField()

    # Payment
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Fulfillment
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)

    # Notes
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generate unique order number."""
        import uuid
        return f"ORD-{uuid.uuid4().hex[:8].upper()}"

    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled."""
        return self.status in [Constants.PENDING, Constants.PAID]

    def cancel(self, reason="Customer request"):
        """Cancel the order and restore inventory."""
        if not self.can_be_cancelled:
            raise ValueError("Order cannot be cancelled in current status.")

        # Restore inventory
        for item in self.items.all():  # type: ignore
            item.product.inventory += item.quantity
            item.product.save(update_fields=['inventory'])

        self.status = Constants.CANCELLED
        self.internal_notes += f"\nCancelled: {reason}"
        self.save(update_fields=['status', 'internal_notes'])


class OrderItem(BaseModel):
    """Order item model."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items'
    )

    # Product snapshot (preserve data at time of order)
    product_sku = models.CharField(max_length=100)
    product_title = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Vendor info (for earnings calculation)
    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='order_items_as_vendor'
    )

    def __str__(self):
        return f"{self.quantity}x {self.product_title} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        # Capture product snapshot
        if not self.product_sku:
            self.product_sku = self.product.sku
            self.product_title = self.product.title
            self.product_price = self.product.price
            self.vendor = self.product.vendor

        # Calculate prices
        if not self.unit_price:
            self.unit_price = self.product.current_price

        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class ShippingMethod(models.Model):
    """Shipping method model."""

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_days_min = models.PositiveIntegerField()
    estimated_days_max = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"

    @property
    def estimated_delivery(self):
        """Get estimated delivery time."""
        if self.estimated_days_min == self.estimated_days_max:
            return f"{self.estimated_days_min} days"
        return f"{self.estimated_days_min}-{self.estimated_days_max} days"


class PaymentIntent(BaseModel):
    """Payment intent model (for payment processing)."""

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_intent'
    )
    # External payment processor ID
    payment_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('succeeded', 'Succeeded'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    payment_method = models.CharField(max_length=50)

    # Processor-specific data
    processor_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Payment for {self.order.order_number}"


class VendorEarnings(BaseModel):
    """Vendor earnings tracking."""

    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='earnings'
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='vendor_earnings'
    )
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('available', 'Available'),
            ('paid', 'Paid'),
        ],
        default='pending'
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['vendor', 'order']

    def __str__(self):
        return f"Earnings for {self.vendor.email} - {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.net_amount:
            self.net_amount = self.gross_amount - self.platform_fee
        super().save(*args, **kwargs)
