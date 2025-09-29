"""Orders admin configuration."""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Cart, CartItem, Order, OrderItem, ShippingMethod, PaymentIntent, VendorEarnings


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Cart admin configuration."""

    list_display = ['cart_owner', 'total_items', 'subtotal', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'session_key']

    def cart_owner(self, obj):
        if obj.user:
            return obj.user.email
        return f"Anonymous ({obj.session_key[:8]}...)"
    cart_owner.short_description = 'Owner'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Cart item admin configuration."""

    list_display = ['cart_owner', 'product_title', 'quantity', 'total_price']
    list_filter = ['created_at']
    search_fields = ['cart__user__email', 'product__title']

    def cart_owner(self, obj):
        if obj.cart.user:
            return obj.cart.user.email
        return f"Anonymous ({obj.cart.session_key[:8]}...)"
    cart_owner.short_description = 'Cart Owner'

    def product_title(self, obj):
        return obj.product.title
    product_title.short_description = 'Product'


class OrderItemInline(admin.TabularInline):
    """Order item inline."""
    model = OrderItem
    extra = 0
    readonly_fields = ['product_sku', 'product_title',
                       'unit_price', 'total_price', 'vendor']
    fields = ['product', 'product_sku', 'product_title',
              'quantity', 'unit_price', 'total_price', 'vendor']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order admin configuration."""

    list_display = [
        'order_number', 'user_email', 'status', 'total_amount',
        'payment_status', 'created_at', 'order_actions'
    ]
    list_filter = ['status', 'payment_method', 'created_at', 'paid_at']
    search_fields = ['order_number', 'user__email']
    readonly_fields = [
        'order_number', 'subtotal', 'tax_amount', 'shipping_amount',
        'total_amount', 'created_at', 'updated_at'
    ]
    inlines = [OrderItemInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_amount', 'shipping_amount', 'discount_amount', 'total_amount')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address'),
            'classes': ('collapse',)
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_reference', 'paid_at')
        }),
        ('Fulfillment', {
            'fields': ('shipped_at', 'delivered_at', 'tracking_number')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'internal_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Customer'

    def payment_status(self, obj):
        if obj.paid_at:
            return format_html('<span style="color: green;">✓ Paid</span>')
        return format_html('<span style="color: red;">✗ Unpaid</span>')
    payment_status.short_description = 'Payment'

    def order_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Mark as Paid</a>&nbsp;'
            '<a class="button" href="{}">Mark as Shipped</a>',
            reverse('admin:mark_order_paid', args=[obj.pk]),
            reverse('admin:mark_order_shipped', args=[obj.pk]),
        )
    order_actions.short_description = 'Actions'
    order_actions.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path(
                '<int:order_id>/mark-paid/',
                self.admin_site.admin_view(self.mark_paid),
                name='mark_order_paid',
            ),
            path(
                '<int:order_id>/mark-shipped/',
                self.admin_site.admin_view(self.mark_shipped),
                name='mark_order_shipped',
            ),
        ]
        return custom_urls + urls

    def mark_paid(self, request, order_id):
        from django.shortcuts import redirect
        from django.contrib import messages

        order = Order.objects.get(id=order_id)
        order.status = 'PAID'
        order.paid_at = timezone.now()
        order.save()

        # Update vendor earnings
        VendorEarnings.objects.filter(order=order).update(status='available')

        messages.success(
            request, f'Order {order.order_number} marked as paid.')
        return redirect(reverse('admin:orders_order_changelist'))

    def mark_shipped(self, request, order_id):
        from django.shortcuts import redirect
        from django.contrib import messages

        order = Order.objects.get(id=order_id)
        order.status = 'SHIPPED'
        order.shipped_at = timezone.now()
        order.save()

        messages.success(
            request, f'Order {order.order_number} marked as shipped.')
        return redirect(reverse('admin:orders_order_changelist'))


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Order item admin configuration."""

    list_display = [
        'order_number', 'product_title', 'vendor_name',
        'quantity', 'unit_price', 'total_price'
    ]
    list_filter = ['vendor', 'created_at']
    search_fields = ['order__order_number', 'product_title', 'vendor__email']

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'

    def vendor_name(self, obj):
        return obj.vendor.full_name
    vendor_name.short_description = 'Vendor'


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    """Shipping method admin configuration."""

    list_display = ['name', 'price', 'estimated_delivery', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['price', 'is_active']


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    """Payment intent admin configuration."""

    list_display = ['order_number', 'payment_id',
                    'amount', 'status', 'payment_method']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order__order_number', 'payment_id']

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'


@admin.register(VendorEarnings)
class VendorEarningsAdmin(admin.ModelAdmin):
    """Vendor earnings admin configuration."""

    list_display = [
        'vendor_name', 'order_number', 'gross_amount',
        'platform_fee', 'net_amount', 'status', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'paid_at']
    search_fields = ['vendor__email', 'order__order_number']
    readonly_fields = ['net_amount', 'created_at', 'updated_at']

    # ✅ This must be a list of action method names
    actions = ['mark_as_paid']

    def vendor_name(self, obj):
        return obj.vendor.full_name
    vendor_name.short_description = 'Vendor'

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'

    def mark_as_paid(self, request, queryset):
        """Admin action to mark selected earnings as paid."""
        updated = queryset.update(status='paid', paid_at=timezone.now())
        self.message_user(request, f'{updated} earnings marked as paid.')
    mark_as_paid.short_description = 'Mark selected earnings as paid'
