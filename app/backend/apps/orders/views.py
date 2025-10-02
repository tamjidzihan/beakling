"""Orders views."""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample
from apps.common.permissions import IsAdminOnly, IsVendorOrReadOnly
from apps.catalog.models import Product
from .models import Cart, CartItem, Order, OrderItem, ShippingMethod, VendorEarnings
from .serializers import (
    CartSerializer, CartItemSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, ShippingMethodSerializer, VendorEarningsSerializer
)
from decimal import Decimal


def get_or_create_cart(request):
    """Get or create cart for user or session."""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Merge session cart if exists
        session_key = request.session.session_key
        if session_key and not created:
            try:
                session_cart = Cart.objects.get(session_key=session_key)
                # Merge items
                for session_item in session_cart.items.all():  # type: ignore
                    cart_item, item_created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=session_item.product,
                        defaults={'quantity': session_item.quantity}
                    )
                    if not item_created:
                        cart_item.quantity += session_item.quantity
                        cart_item.save()

                # Delete session cart
                session_cart.delete()
            except Cart.DoesNotExist:
                pass
    else:
        # Anonymous user
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)

    return cart


@extend_schema_view(
    get=extend_schema(
        tags=['Cart'],
        summary="Get cart details",
        description="Get current user's cart details including items, subtotal, and savings.",
        responses={
            200: CartSerializer,
        }
    )
)
class CartView(generics.RetrieveAPIView):
    """Get current user's cart."""
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_or_create_cart(self.request)


@extend_schema_view(
    get=extend_schema(
        tags=['Cart'],
        summary="List cart items",
        description="List all items in the current user's cart.",
        responses={
            200: CartItemSerializer(many=True),
        }
    ),
    post=extend_schema(
        tags=['Cart'],
        summary="Add item to cart",
        description="Add a product to the shopping cart.",
        request=CartItemSerializer,
        examples=[
            OpenApiExample(
                'Add to cart example',
                value={
                    'product_id': 1,
                    'quantity': 2
                },
                request_only=True
            )
        ]
    )
)
class CartItemListView(generics.ListCreateAPIView):
    """List and add items to cart."""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        cart = get_or_create_cart(self.request)
        return cart.items.all().select_related('product__category')  # type: ignore

    def perform_create(self, serializer):
        cart = get_or_create_cart(self.request)
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        # Check if item already exists in cart
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            cart_item.quantity += quantity

            # Check inventory
            if cart_item.quantity > cart_item.product.inventory:
                cart_item.quantity = cart_item.product.inventory

            cart_item.save()
            serializer.instance = cart_item
        except CartItem.DoesNotExist:
            serializer.save(cart=cart, product_id=product_id)


@extend_schema_view(
    get=extend_schema(
        tags=['Cart'],
        summary="Get cart item",
        description="Retrieve specific cart item details.",
        responses={
            200: CartItemSerializer,
        }
    ),
    put=extend_schema(
        tags=['Cart'],
        summary="Update cart item",
        description="Update the quantity of a specific cart item.",
        request=CartItemSerializer,
        examples=[
            OpenApiExample(
                'Update cart item example',
                value={
                    'quantity': 3
                },
                request_only=True
            )
        ]
    ),
    patch=extend_schema(
        tags=['Cart'],
        summary="Partial update cart item",
        description="Partially update a cart item.",
        request=CartItemSerializer,
    ),
    delete=extend_schema(
        tags=['Cart'],
        summary="Remove cart item",
        description="Remove a specific item from the shopping cart.",
    )
)
class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update or remove cart items."""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        cart = get_or_create_cart(self.request)
        return cart.items.all()  # type: ignore


@extend_schema(
    tags=['Cart'],
    summary="Merge carts",
    description="Merge session cart with user cart after login.",
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            'Merge cart request',
            value={
                'session_key': 'session123456'
            },
            request_only=True
        )
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        401: OpenApiTypes.OBJECT
    }
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def merge_cart(request):
    """Merge session cart with user cart after login."""
    if not request.user.is_authenticated:
        return Response({'error': 'User must be authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)

    session_key = request.data.get('session_key')
    if not session_key:
        return Response({'message': 'No session cart to merge.'})

    try:
        session_cart = Cart.objects.get(session_key=session_key)
        user_cart, created = Cart.objects.get_or_create(user=request.user)

        # Merge items
        merged_count = 0
        for session_item in session_cart.items.all():  # type: ignore
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=session_item.product,
                defaults={'quantity': session_item.quantity}
            )
            if not item_created:
                cart_item.quantity += session_item.quantity
                # Ensure we don't exceed inventory
                if cart_item.quantity > cart_item.product.inventory:
                    cart_item.quantity = cart_item.product.inventory
                cart_item.save()
            merged_count += 1

        # Delete session cart
        session_cart.delete()

        return Response({
            'message': f'Merged {merged_count} items into cart.',
            'cart': CartSerializer(user_cart).data
        })

    except Cart.DoesNotExist:
        return Response({'message': 'Session cart not found.'})


@extend_schema_view(
    get=extend_schema(
        tags=['Shipping'],
        summary="List shipping methods",
        description="List all available shipping methods.",
        responses={
            200: ShippingMethodSerializer(many=True),
        }
    )
)
class ShippingMethodListView(generics.ListAPIView):
    """List available shipping methods."""
    queryset = ShippingMethod.objects.filter(is_active=True)
    serializer_class = ShippingMethodSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema_view(
    get=extend_schema(
        tags=['Orders'],
        summary="List user orders",
        description="List authenticated user's order history.",
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of items per page'
            )
        ],
        responses={
            200: OrderListSerializer(many=True),
        }
    )
)
class OrderListView(generics.ListAPIView):
    """List user's orders."""
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related('user')


@extend_schema_view(
    get=extend_schema(
        tags=['Orders'],
        summary="Get order details",
        description="Retrieve detailed information for a specific order.",
        responses={
            200: OrderDetailSerializer,
            404: OpenApiTypes.OBJECT
        }
    )
)
class OrderDetailView(generics.RetrieveAPIView):
    """Order detail view."""
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


@extend_schema_view(
    post=extend_schema(
        tags=['Orders'],
        summary="Create order",
        description="Create a new order from cart items.",
        request=OrderCreateSerializer,
        examples=[
            OpenApiExample(
                'Create order example',
                value={
                    'shipping_address_id': 1,
                    'billing_address_id': 2,
                    'shipping_method_id': 1,
                    'payment_method': 'stripe',
                    'customer_notes': 'Please deliver after 5 PM'
                },
                request_only=True
            )
        ],
        responses={
            201: OrderDetailSerializer,
            400: OpenApiTypes.OBJECT
        }
    )
)
class OrderCreateView(generics.CreateAPIView):
    """Create new order."""
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = serializer.save()

        # Create vendor earnings records
        vendor_totals = {}
        for item in order.items.all():
            vendor_id = item.vendor.id
            if vendor_id not in vendor_totals:
                vendor_totals[vendor_id] = {
                    'vendor': item.vendor,
                    'gross_amount': 0
                }
            vendor_totals[vendor_id]['gross_amount'] += item.total_price

        for vendor_data in vendor_totals.values():
            gross_amount = vendor_data['gross_amount']
            platform_fee = gross_amount * Decimal('0.05')  # 5% platform fee

            VendorEarnings.objects.create(
                vendor=vendor_data['vendor'],
                order=order,
                gross_amount=gross_amount,
                platform_fee=platform_fee
            )

        return Response(
            OrderDetailSerializer(order).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    tags=['Orders'],
    summary="Cancel order",
    description="Cancel an order that is in a cancellable status.",
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            'Cancel order request',
            value={
                'reason': 'Changed my mind'
            },
            request_only=True
        )
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT
    }
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order."""
    try:
        order = Order.objects.get(id=order_id, user=request.user)

        if not order.can_be_cancelled:
            return Response(
                {'error': 'Order cannot be cancelled in current status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'Customer request')
        order.cancel(reason)

        return Response({'message': 'Order cancelled successfully.'})

    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=['Orders'],
    summary="Update order status",
    description="Update order status (Admin only).",
    request=OpenApiTypes.OBJECT,
    examples=[
        OpenApiExample(
            'Update status request',
            value={
                'status': 'SHIPPED',
                'tracking_number': 'TRACK123456'
            },
            request_only=True
        )
    ],
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT,
        404: OpenApiTypes.OBJECT,
        500: OpenApiTypes.OBJECT
    }
)
@api_view(['POST'])
@permission_classes([IsAdminOnly])
def update_order_status(request, order_id):
    """Update order status (Admin only)."""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate required fields
    new_status = request.data.get('status')
    if not new_status:
        return Response(
            {'error': 'Status field is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate status value
    valid_statuses = [choice[0]
                      for choice in Order._meta.get_field('status').choices]
    if new_status not in valid_statuses:
        return Response(
            {'error': f'Invalid status. Valid options are: {", ".join(valid_statuses)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    tracking_number = request.data.get('tracking_number', '')

    # Prevent status regression
    old_status = order.status
    if new_status == old_status:
        return Response(
            {'warning': f'Order status is already {new_status}.'},
            status=status.HTTP_200_OK
        )

    # Update order with transaction to ensure data consistency
    try:
        with transaction.atomic():
            order.status = new_status

            # Update timestamps based on status transitions
            if new_status == 'PAID' and old_status != 'PAID':
                order.paid_at = timezone.now()
                # Update vendor earnings to available
                VendorEarnings.objects.filter(
                    order=order).update(status='available')

            elif new_status == 'SHIPPED' and old_status != 'SHIPPED':
                order.shipped_at = timezone.now()
                if tracking_number:
                    order.tracking_number = tracking_number

            elif new_status == 'DELIVERED' and old_status != 'DELIVERED':
                order.delivered_at = timezone.now()
                # Ensure order was shipped before being delivered
                if not order.shipped_at:
                    order.shipped_at = timezone.now()

            order.save()

        return Response({
            'message': f'Order status updated from {old_status} to {new_status}.',
            'order': OrderDetailSerializer(order).data
        })

    except Exception as e:
        return Response(
            {'error': f'Failed to update order status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema_view(
    get=extend_schema(
        tags=['Vendor'],
        summary="List vendor orders",
        description="List orders containing vendor's products.",
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by order status'
            )
        ],
        responses={
            200: OrderListSerializer(many=True),
        }
    )
)
class VendorOrdersView(generics.ListAPIView):
    """List orders for vendor's products."""
    serializer_class = OrderListSerializer
    permission_classes = [IsVendorOrReadOnly]

    def get_queryset(self):
        # Get orders that contain vendor's products
        vendor_orders = Order.objects.filter(
            items__vendor=self.request.user
        ).distinct().select_related('user')

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')  # type: ignore
        if status_filter:
            vendor_orders = vendor_orders.filter(status=status_filter)

        return vendor_orders


@extend_schema_view(
    get=extend_schema(
        tags=['Vendor'],
        summary="List vendor earnings",
        description="List earnings records for the authenticated vendor.",
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by earnings status'
            ),
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter by start date'
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter by end date'
            )
        ],
        responses={
            200: VendorEarningsSerializer(many=True),
        }
    )
)
class VendorEarningsView(generics.ListAPIView):
    """List vendor earnings."""
    serializer_class = VendorEarningsSerializer
    permission_classes = [IsVendorOrReadOnly]

    def get_queryset(self):
        queryset = VendorEarnings.objects.filter(
            vendor=self.request.user
        ).select_related('order__user')

        # Apply filters
        status_filter = self.request.query_params.get('status')  # type: ignore
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        start_date = self.request.query_params.get(  # type: ignore
            'start_date')  # type: ignore
        end_date = self.request.query_params.get('end_date')  # type: ignore
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset


@extend_schema(
    tags=['Vendor'],
    summary="Vendor earnings summary",
    description="Get aggregated earnings summary for the authenticated vendor.",
    parameters=[
        OpenApiParameter(
            name='start_date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Filter by start date'
        ),
        OpenApiParameter(
            name='end_date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description='Filter by end date'
        )
    ],
    responses={
        200: OpenApiTypes.OBJECT,
    }
)
@api_view(['GET'])
@permission_classes([IsVendorOrReadOnly])
def vendor_earnings_summary(request):
    """Get vendor earnings summary."""
    earnings = VendorEarnings.objects.filter(vendor=request.user)

    # Apply date filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        earnings = earnings.filter(created_at__date__gte=start_date)
    if end_date:
        earnings = earnings.filter(created_at__date__lte=end_date)

    summary = earnings.aggregate(
        total_gross=Sum('gross_amount'),
        total_fees=Sum('platform_fee'),
        total_net=Sum('net_amount'),
        pending_amount=Sum('net_amount', filter=Q(status='pending')),
        available_amount=Sum('net_amount', filter=Q(status='available')),
        paid_amount=Sum('net_amount', filter=Q(status='paid')),
        total_orders=Count('order', distinct=True)
    )

    # Convert None to 0
    for key, value in summary.items():
        if value is None:
            summary[key] = 0

    return Response(summary)


@extend_schema(
    tags=['Analytics'],
    summary="Order analytics",
    description="Get comprehensive order analytics (Admin only).",
    parameters=[
        OpenApiParameter(
            name='days',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of days to analyze (default: 30)',
            default=30
        )
    ],
    responses={
        200: OpenApiTypes.OBJECT,
    }
)
@api_view(['GET'])
@permission_classes([IsAdminOnly])
def order_analytics(request):
    """Get order analytics (Admin only)."""
    from django.utils import timezone
    from datetime import timedelta

    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    orders = Order.objects.filter(created_at__gte=start_date)

    analytics = {
        'total_orders': orders.count(),
        'total_revenue': orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'average_order_value': 0,
        'status_breakdown': {},
        'daily_orders': [],
        'top_products': []
    }

    if analytics['total_orders'] > 0:
        analytics['average_order_value'] = analytics['total_revenue'] / \
            analytics['total_orders']

    # Status breakdown
    from django.db.models import Count
    status_data = orders.values('status').annotate(count=Count('id'))
    for item in status_data:
        analytics['status_breakdown'][item['status']] = item['count']

    # Daily orders for the last 7 days
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        daily_count = orders.filter(created_at__date=date).count()
        analytics['daily_orders'].append({
            'date': date.isoformat(),
            'count': daily_count
        })

    # Top selling products
    top_products = OrderItem.objects.filter(
        order__created_at__gte=start_date
    ).values('product_title').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:10]

    analytics['top_products'] = list(top_products)

    return Response(analytics)
