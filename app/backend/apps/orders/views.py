"""Orders views."""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.common.permissions import IsAdminOnly, IsVendorOrReadOnly
from apps.catalog.models import Product
from .models import Cart, CartItem, Order, OrderItem, ShippingMethod, VendorEarnings
from .serializers import (
    CartSerializer, CartItemSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, ShippingMethodSerializer, VendorEarningsSerializer
)


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
                for session_item in session_cart.items.all():
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


class CartView(generics.RetrieveAPIView):
    """Get current user's cart."""
    serializer_class = CartSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_or_create_cart(self.request)


class CartItemListView(generics.ListCreateAPIView):
    """List and add items to cart."""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        cart = get_or_create_cart(self.request)
        return cart.items.all().select_related('product__category')

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


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update or remove cart items."""
    serializer_class = CartItemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        cart = get_or_create_cart(self.request)
        return cart.items.all()


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
        for session_item in session_cart.items.all():
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


class ShippingMethodListView(generics.ListAPIView):
    """List available shipping methods."""
    queryset = ShippingMethod.objects.filter(is_active=True)
    serializer_class = ShippingMethodSerializer
    permission_classes = [permissions.AllowAny]


class OrderListView(generics.ListAPIView):
    """List user's orders."""
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related('user')


class OrderDetailView(generics.RetrieveAPIView):
    """Order detail view."""
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


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
            platform_fee = gross_amount * 0.05  # 5% platform fee
            
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


class VendorOrdersView(generics.ListAPIView):
    """List orders for vendor's products."""
    serializer_class = OrderListSerializer
    permission_classes = [IsVendorOrReadOnly]

    def get_queryset(self):
        # Get orders that contain vendor's products
        vendor_orders = Order.objects.filter(
            items__vendor=self.request.user
        ).distinct().select_related('user')
        
        return vendor_orders


class VendorEarningsView(generics.ListAPIView):
    """List vendor earnings."""
    serializer_class = VendorEarningsSerializer
    permission_classes = [IsVendorOrReadOnly]

    def get_queryset(self):
        return VendorEarnings.objects.filter(
            vendor=self.request.user
        ).select_related('order__user')


@api_view(['GET'])
@permission_classes([IsVendorOrReadOnly])
def vendor_earnings_summary(request):
    """Get vendor earnings summary."""
    earnings = VendorEarnings.objects.filter(vendor=request.user)
    
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


@api_view(['POST'])
@permission_classes([IsAdminOnly])
def update_order_status(request, order_id):
    """Update order status (Admin only)."""
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.data.get('status')
        tracking_number = request.data.get('tracking_number', '')
        
        if new_status not in dict(Order._meta.get_field('status').choices):
            return Response(
                {'error': 'Invalid status.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = order.status
        order.status = new_status
        
        # Update timestamps based on status
        if new_status == 'PAID' and old_status != 'PAID':
            order.paid_at = timezone.now()
            # Update vendor earnings to available
            VendorEarnings.objects.filter(order=order).update(status='available')
        
        elif new_status == 'SHIPPED' and old_status != 'SHIPPED':
            order.shipped_at = timezone.now()
            if tracking_number:
                order.tracking_number = tracking_number
        
        elif new_status == 'DELIVERED' and old_status != 'DELIVERED':
            order.delivered_at = timezone.now()
        
        order.save()
        
        return Response({
            'message': f'Order status updated to {new_status}.',
            'order': OrderDetailSerializer(order).data
        })
        
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found.'},
            status=status.HTTP_404_NOT_FOUND
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
        analytics['average_order_value'] = analytics['total_revenue'] / analytics['total_orders']
    
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