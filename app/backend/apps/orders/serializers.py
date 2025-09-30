"""Orders serializers."""

from rest_framework import serializers
from django.db import transaction
from decimal import Decimal
from apps.common.serializers import TimestampedSerializer
from apps.catalog.serializers import ProductListSerializer
from apps.users.serializers import AddressSerializer
from .models import Cart, CartItem, Order, OrderItem, ShippingMethod, PaymentIntent, VendorEarnings


class CartItemSerializer(TimestampedSerializer):
    """Cart item serializer."""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    unit_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_id', 'quantity',
            'unit_price', 'total_price', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_product_id(self, value):
        from apps.catalog.models import Product
        try:
            product = Product.objects.get(id=value, is_active=True)
            if product.inventory < 1:
                raise serializers.ValidationError("Product is out of stock.")
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")
        return value

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")

        # Check if we have enough inventory
        product_id = self.initial_data.get('product_id')  # type: ignore
        if product_id:
            try:
                from apps.catalog.models import Product
                product = Product.objects.get(id=product_id, is_active=True)
                if value > product.inventory:
                    raise serializers.ValidationError(
                        f"Only {product.inventory} items available in stock."
                    )
            except Product.DoesNotExist:
                pass  # Will be caught by product_id validation

        return value


class CartSerializer(TimestampedSerializer):
    """Cart serializer."""

    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    total_savings = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'total_items', 'subtotal', 'total_savings',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ShippingMethodSerializer(serializers.ModelSerializer):
    """Shipping method serializer."""

    estimated_delivery = serializers.CharField(read_only=True)

    class Meta:
        model = ShippingMethod
        fields = [
            'id', 'name', 'description', 'price',
            'estimated_days_min', 'estimated_days_max',
            'estimated_delivery', 'is_active'
        ]


class OrderItemSerializer(TimestampedSerializer):
    """Order item serializer."""

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_sku', 'product_title', 'product_price',
            'quantity', 'unit_price', 'total_price', 'vendor',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderListSerializer(TimestampedSerializer):
    """Order list serializer."""

    items_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'total_amount', 'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(TimestampedSerializer):
    """Order detail serializer."""

    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'status_display',
            'subtotal', 'tax_amount', 'shipping_amount', 'discount_amount',
            'total_amount', 'shipping_address', 'billing_address',
            'payment_method', 'payment_reference', 'paid_at',
            'shipped_at', 'delivered_at', 'tracking_number',
            'customer_notes', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'payment_reference', 'paid_at',
            'shipped_at', 'delivered_at', 'created_at', 'updated_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Order creation serializer."""

    shipping_address_id = serializers.IntegerField()
    billing_address_id = serializers.IntegerField()
    shipping_method_id = serializers.IntegerField()
    payment_method = serializers.ChoiceField(
        choices=[
            ('stripe', 'Credit Card'),
            ('paypal', 'PayPal'),
            ('cash_on_delivery', 'Cash on Delivery'),
        ]
    )
    customer_notes = serializers.CharField(
        max_length=500, required=False, allow_blank=True)

    def validate_shipping_address_id(self, value):
        from apps.users.models import Address
        user = self.context['request'].user
        try:
            Address.objects.get(id=value, user=user, type='shipping')
        except Address.DoesNotExist:
            raise serializers.ValidationError("Invalid shipping address.")
        return value

    def validate_billing_address_id(self, value):
        from apps.users.models import Address
        user = self.context['request'].user
        try:
            Address.objects.get(id=value, user=user, type='billing')
        except Address.DoesNotExist:
            raise serializers.ValidationError("Invalid billing address.")
        return value

    def validate_shipping_method_id(self, value):
        try:
            ShippingMethod.objects.get(id=value, is_active=True)
        except ShippingMethod.DoesNotExist:
            raise serializers.ValidationError("Invalid shipping method.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        from apps.users.models import Address

        user = self.context['request'].user

        # Get addresses
        shipping_address = Address.objects.get(
            id=validated_data['shipping_address_id'],
            user=user,
            type='shipping'
        )
        billing_address = Address.objects.get(
            id=validated_data['billing_address_id'],
            user=user,
            type='billing'
        )

        # Get shipping method
        shipping_method = ShippingMethod.objects.get(
            id=validated_data['shipping_method_id'],
            is_active=True
        )

        # Get user's cart
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart is empty.")

        if not cart.items.exists():  # type: ignore
            raise serializers.ValidationError("Cart is empty.")

        # Calculate totals
        subtotal = cart.subtotal
        tax_rate = Decimal('0.08')  # 8% tax rate
        tax_amount = subtotal * tax_rate
        shipping_amount = shipping_method.price
        total_amount = subtotal + tax_amount + shipping_amount

        # Create order
        order = Order.objects.create(
            user=user,
            status='PENDING',
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            total_amount=total_amount,
            shipping_address={
                'first_name': shipping_address.first_name,
                'last_name': shipping_address.last_name,
                'company': shipping_address.company,
                'address_line_1': shipping_address.address_line_1,
                'address_line_2': shipping_address.address_line_2,
                'city': shipping_address.city,
                'state': shipping_address.state,
                'postal_code': shipping_address.postal_code,
                'country': shipping_address.country,
                'phone': shipping_address.phone,
            },
            billing_address={
                'first_name': billing_address.first_name,
                'last_name': billing_address.last_name,
                'company': billing_address.company,
                'address_line_1': billing_address.address_line_1,
                'address_line_2': billing_address.address_line_2,
                'city': billing_address.city,
                'state': billing_address.state,
                'postal_code': billing_address.postal_code,
                'country': billing_address.country,
                'phone': billing_address.phone,
            },
            payment_method=validated_data['payment_method'],
            customer_notes=validated_data.get('customer_notes', '')
        )

        # Create order items and update inventory
        for cart_item in cart.items.all():  # type: ignore
            # Check inventory again
            if cart_item.product.inventory < cart_item.quantity:
                raise serializers.ValidationError(
                    f"Insufficient inventory for {cart_item.product.title}."
                )

            # Create order item
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price
            )

            # Update inventory
            cart_item.product.inventory -= cart_item.quantity
            cart_item.product.save(update_fields=['inventory'])

        # Clear cart
        cart.items.all().delete()  # type: ignore

        return order


class PaymentIntentSerializer(TimestampedSerializer):
    """Payment intent serializer."""

    class Meta:
        model = PaymentIntent
        fields = [
            'id', 'payment_id', 'amount', 'currency', 'status',
            'payment_method', 'processor_data', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VendorEarningsSerializer(TimestampedSerializer):
    """Vendor earnings serializer."""

    order_number = serializers.CharField(
        source='order.order_number', read_only=True)
    customer_email = serializers.CharField(
        source='order.user.email', read_only=True)

    class Meta:
        model = VendorEarnings
        fields = [
            'id', 'order_number', 'customer_email', 'gross_amount',
            'platform_fee', 'net_amount', 'status', 'paid_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
