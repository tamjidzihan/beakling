"""User views."""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from drf_spectacular.utils import extend_schema,  OpenApiExample, OpenApiResponse
from apps.common.permissions import IsAdminOnly
from .models import User, VendorProfile, CustomerProfile, Address
from .serializers import (
    UserSerializer, UserRegistrationSerializer, PasswordChangeSerializer,
    VendorProfileSerializer, VendorApplicationSerializer, VendorApprovalSerializer,
    CustomerProfileSerializer, AddressSerializer, GoogleAuthSerializer
)


@extend_schema(tags=['Authentication'])
class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user account.

    Creates a new user account and returns JWT tokens for immediate authentication.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register new user",
        description="""
        Register a new user with email, password, and basic information.
        Returns JWT tokens upon successful registration.

        **Required fields:** email, password, first_name, last_name
        """,
        examples=[
            OpenApiExample(
                'Registration Example',
                value={
                    'email': 'user@example.com',
                    'password': 'securepassword123',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'role': 'CUSTOMER'
                },
                request_only=True
            )
        ],
        responses={
            201: OpenApiResponse(
                description="User created successfully",
                response=UserRegistrationSerializer
            ),
            400: OpenApiResponse(description="Invalid input data")
        }
    )
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


@extend_schema(tags=['Users'])
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated user's profile.

    Allows users to view and modify their own profile information.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get user profile",
        description="Retrieve the authenticated user's profile information.",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update user profile",
        description="Update the authenticated user's profile information.",
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update user profile",
        description="Partially update the authenticated user's profile information.",
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


@extend_schema(tags=['Authentication'])
class PasswordChangeView(generics.UpdateAPIView):
    """
    Change user password.

    Allows authenticated users to change their password.
    """
    serializer_class = PasswordChangeSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Change password",
        description="""
        Change the authenticated user's password.

        **Required fields:** current_password, new_password
        """,
        examples=[
            OpenApiExample(
                'Password Change Example',
                value={
                    'current_password': 'oldpassword123',
                    'new_password': 'newsecurepassword456'
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(description="Password updated successfully"),
            400: OpenApiResponse(description="Invalid current password"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'message': 'Password updated successfully.'})

    def get_object(self):
        return self.request.user


@extend_schema(tags=['Vendors'])
class VendorApplicationView(generics.CreateAPIView):
    """
    Apply to become a vendor.

    Submit an application to become a vendor on the platform.
    """
    serializer_class = VendorApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Apply as vendor",
        description="""
        Submit a vendor application. Users can only have one active application.

        **Required fields:** business_name, business_address, business_phone, business_email
        """,
        responses={
            201: OpenApiResponse(description="Application submitted successfully"),
            400: OpenApiResponse(description="Already has vendor application"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def create(self, request, *args, **kwargs):
        # Check if user already has a vendor profile
        if hasattr(request.user, 'vendor_profile'):
            return Response(
                {'error': 'You already have a vendor application.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)


@extend_schema(tags=['Vendors', 'Admin'])
class VendorListView(generics.ListAPIView):
    """
    List all vendor applications (Admin only).

    Retrieve a list of all vendor applications for admin review.
    """
    queryset = VendorProfile.objects.all()
    serializer_class = VendorProfileSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        summary="List vendor applications",
        description="Retrieve all vendor applications (Admin access required).",
        responses={
            200: VendorProfileSerializer(many=True),
            403: OpenApiResponse(description="Admin access required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=['Vendors', 'Admin'])
class VendorApprovalView(generics.UpdateAPIView):
    """
    Approve or reject vendor application (Admin only).

    Admin endpoint to manage vendor application approvals.
    """
    queryset = VendorProfile.objects.all()
    serializer_class = VendorApprovalSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        summary="Approve/reject vendor",
        description="""
        Approve or reject a vendor application.

        **Required parameters:**
        - action: "approve" or "reject"
        - rejection_reason: Required if action is "reject"
        """,
        examples=[
            OpenApiExample(
                'Approve Example',
                value={'action': 'approve'},
                request_only=True
            ),
            OpenApiExample(
                'Reject Example',
                value={
                    'action': 'reject',
                    'rejection_reason': 'Incomplete business information'
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(description="Action completed successfully"),
            400: OpenApiResponse(description="Invalid action"),
            403: OpenApiResponse(description="Admin access required"),
            404: OpenApiResponse(description="Vendor application not found")
        }
    )
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


@extend_schema(tags=['Customers'])
class CustomerProfileView(generics.RetrieveUpdateAPIView):
    """
    Manage customer profile.

    Retrieve or update customer-specific profile information.
    """
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get customer profile",
        description="Retrieve customer profile information.",
        responses={
            200: CustomerProfileSerializer,
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update customer profile",
        description="Update customer profile information.",
        responses={
            200: CustomerProfileSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    def get_object(self):
        profile, created = CustomerProfile.objects.get_or_create(
            user=self.request.user
        )
        return profile


@extend_schema(tags=['Addresses'])
class AddressListCreateView(generics.ListCreateAPIView):
    """
    Manage user addresses.

    List all addresses or create a new address for the authenticated user.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List addresses",
        description="Retrieve all addresses for the authenticated user.",
        responses={
            200: AddressSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create address",
        description="Create a new address for the authenticated user.",
        responses={
            201: AddressSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()  # For drf-spectacular
        return Address.objects.filter(user=self.request.user)


@extend_schema(tags=['Addresses'])
class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Manage specific address.

    Retrieve, update, or delete a specific address.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get address",
        description="Retrieve a specific address by ID.",
        responses={
            200: AddressSerializer,
            404: OpenApiResponse(description="Address not found"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update address",
        description="Update a specific address by ID.",
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            404: OpenApiResponse(description="Address not found"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Delete address",
        description="Delete a specific address by ID.",
        responses={
            204: OpenApiResponse(description="Address deleted successfully"),
            404: OpenApiResponse(description="Address not found"),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


@extend_schema(
    tags=['Authentication'],
    summary="Google OAuth authentication",
    description="""
    Authenticate using Google OAuth.
    
    **Note:** This endpoint is not fully implemented yet.
    """,
    responses={
        501: OpenApiResponse(description="Not implemented yet")
    }
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_auth(request):
    """Google OAuth authentication."""
    serializer = GoogleAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # TODO: Implement Google token verification
    access_token = serializer.validated_data['access_token']  # type: ignore

    return Response({
        'message': 'Google authentication not fully implemented yet.',
        'access_token': access_token
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@extend_schema(
    tags=['Admin', 'Statistics'],
    summary="Get user statistics",
    description="Retrieve user statistics (Admin access required).",
    responses={
        200: OpenApiResponse(description="Statistics retrieved successfully"),
        403: OpenApiResponse(description="Admin access required")
    }
)
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
