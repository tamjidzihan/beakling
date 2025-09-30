"""Orders URLs."""

from django.urls import path
from . import views

urlpatterns = [
    # Cart
    path('cart/', views.CartView.as_view(), name='cart_detail'),
    path('cart/items/', views.CartItemListView.as_view(), name='cart_items'),
    path('cart/items/<int:pk>/', views.CartItemDetailView.as_view(),
         name='cart_item_detail'),
    path('cart/merge/', views.merge_cart, name='merge_cart'),

    # Shipping
    path('shipping/methods/', views.ShippingMethodListView.as_view(),
         name='shipping_methods'),

    # Orders
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:order_id>/cancel/',
         views.cancel_order, name='cancel_order'),
    path('orders/<int:order_id>/status/',
         views.update_order_status, name='update_order_status'),

    # Vendor Orders & Earnings
    path('vendor/orders/', views.VendorOrdersView.as_view(), name='vendor_orders'),
    path('vendor/earnings/', views.VendorEarningsView.as_view(),
         name='vendor_earnings'),
    path('vendor/earnings/summary/', views.vendor_earnings_summary,
         name='vendor_earnings_summary'),

    # Analytics (Admin)
    path('analytics/', views.order_analytics, name='order_analytics'),
]
