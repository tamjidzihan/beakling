"""Common permissions."""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsVendorOrReadOnly(permissions.BasePermission):
    """
    Custom permission for vendor operations.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_authenticated and
            request.user.role == 'VENDOR' and
            request.user.is_vendor_approved
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if the user is the vendor who owns this product
        return (
            hasattr(obj, 'vendor') and
            obj.vendor == request.user and
            request.user.role == 'VENDOR' and
            request.user.is_vendor_approved
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission for admin-only operations.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsAdminOnly(permissions.BasePermission):
    """
    Permission that allows access only to admin users.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


class IsCustomerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for customer operations.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.role in ['CUSTOMER', 'ADMIN']
