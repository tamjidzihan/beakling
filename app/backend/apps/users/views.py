"""User views."""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from apps.common.permissions import IsAdminOnly
from .models import User, VendorProfile, CustomerProfile, Address
from .serializers import (
    UserSerializer, UserRegistrationSerializer, PasswordChangeSerializer,
    VendorProfileSerializer, VendorApplicationSerializer,
    CustomerProfileSerializer, AddressSerializer, GoogleAuthSerializer
)


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeView(generics.UpdateAPIView):
    """Password change view."""
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'message': 'Password updated successfully.'})


class VendorApplicationView(generics.CreateAPIView):
    """Vendor application endpoint."""
    serializer_class = VendorApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Check if user already has a vendor profile
        if hasattr(request.user, 'vendor_profile'):
            return Response(
                {'error': 'You already have a vendor application.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)


class VendorListView(generics.ListAPIView):
    """List all vendor applications (Admin only)."""
    queryset = VendorProfile.objects.all()
    serializer_class = VendorProfileSerializer
    permission_classes = [IsAdminOnly]


class VendorApprovalView(generics.UpdateAPIView):
    """Approve/reject vendor application (Admin only)."""
    queryset = VendorProfile.objects.all()
    permission_classes = [IsAdminOnly]

    def update(self, request, *args, **kwargs):
        vendor_profile = self.get_object()
        action = request.data.get('action')  # 'approve' or 'reject'
        rejection_reason = request.data.get('rejection_reason', '')

        if action == 'approve':
            vendor_profile.user.is_vendor_approved = True
            vendor_profile.user.save()
            vendor_profile.approval_date = timezone.now()
            vendor_profile.approved_by = request.user
            vendor_profile.rejection_reason = ''
            vendor_profile.save()

            return Response({'message': 'Vendor approved successfully.'})

        elif action == 'reject':
            vendor_profile.user.is_vendor_approved = False
            vendor_profile.user.save()
            vendor_profile.approval_date = None
            vendor_profile.approved_by = None
            vendor_profile.rejection_reason = rejection_reason
            vendor_profile.save()

            return Response({'message': 'Vendor rejected successfully.'})

        return Response(
            {'error': 'Invalid action. Use "approve" or "reject".'},
            status=status.HTTP_400_BAD_REQUEST
        )


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """Customer profile view."""
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = CustomerProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile


class AddressListCreateView(generics.ListCreateAPIView):
    """List and create user addresses."""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Address detail view."""
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_auth(request):
    """Google OAuth authentication."""
    serializer = GoogleAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # TODO: Implement Google token verification
    # This is a placeholder implementation
    access_token = serializer.validated_data['access_token']  # type: ignore

    # In a real implementation, you would:
    # 1. Verify the Google access token
    # 2. Get user info from Google API
    # 3. Create or get the user
    # 4. Return JWT tokens

    return Response({
        'message': 'Google authentication not fully implemented yet.',
        'access_token': access_token
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(['GET'])
@permission_classes([IsAdminOnly])
def user_stats(request):
    """Get user statistics (Admin only)."""
    total_users = User.objects.count()
    customers = User.objects.filter(role='CUSTOMER').count()
    vendors = User.objects.filter(role='VENDOR').count()
    approved_vendors = User.objects.filter(
        role='VENDOR',
        is_vendor_approved=True
    ).count()
    pending_vendors = User.objects.filter(
        role='VENDOR',
        is_vendor_approved=False
    ).count()

    return Response({
        'total_users': total_users,
        'customers': customers,
        'vendors': vendors,
        'approved_vendors': approved_vendors,
        'pending_vendors': pending_vendors,
    })
