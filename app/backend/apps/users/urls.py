"""User URLs."""

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.utils import extend_schema
from . import views

# Add schema extensions to JWT views
extend_schema(tags=['Authentication'])(TokenObtainPairView)
extend_schema(tags=['Authentication'])(TokenRefreshView)
extend_schema(tags=['Authentication'])(TokenVerifyView)

urlpatterns = [
    # JWT Authentication
    path('jwt/create/', TokenObtainPairView.as_view(), name='jwt_create'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='jwt_refresh'),
    path('jwt/verify/', TokenVerifyView.as_view(), name='jwt_verify'),

    # User Management
    path('register/', views.UserRegistrationView.as_view(), name='user_register'),
    path('me/', views.UserProfileView.as_view(), name='user_profile'),
    path('password/change/', views.PasswordChangeView.as_view(),
         name='password_change'),

    # Google OAuth
    # path('google/', views.google_auth, name='google_auth'),

    # Vendor Management
    path('vendors/apply/', views.VendorApplicationView.as_view(), name='vendor_apply'),
    path('vendors/', views.VendorListView.as_view(), name='vendor_list'),
    path('vendors/<int:pk>/approve/',
         views.VendorApprovalView.as_view(), name='vendor_approve'),

    # Customer Profile
    path('customer/profile/', views.CustomerProfileView.as_view(),
         name='customer_profile'),

    # Addresses
    path('addresses/', views.AddressListCreateView.as_view(), name='address_list'),
    path('addresses/<int:pk>/', views.AddressDetailView.as_view(),
         name='address_detail'),

    # Stats
    path('stats/', views.user_stats, name='user_stats'),
]
