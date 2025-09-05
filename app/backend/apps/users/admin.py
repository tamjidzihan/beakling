"""User admin configuration."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import User, VendorProfile, CustomerProfile, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin configuration."""

    list_display = [
        'email', 'first_name', 'last_name', 'role',
        'is_vendor_approved', 'is_active', 'created_at'
    ]
    list_filter = ['role', 'is_vendor_approved', 'is_active', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
            'fields': ('first_name', 'last_name', 'phone', 'date_of_birth', 'avatar')
        }),
        ('Permissions', {
            'fields': ('role', 'is_vendor_approved', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Important dates', {
         'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """Vendor profile admin configuration."""

    list_display = [
        'business_name', 'user_email', 'application_date',
        'is_approved', 'approved_by'
    ]
    list_filter = ['user__is_vendor_approved',
                   'application_date', 'approval_date']
    search_fields = ['business_name', 'user__email', 'business_email']
    ordering = ['-application_date']

    fieldsets = (
        ('Business Information', {
            'fields': ('business_name', 'business_description', 'business_address',
                       'business_phone', 'business_email', 'tax_id', 'website')
        }),
        ('Application Status', {
            'fields': ('user', 'application_date', 'approval_date',
                       'approved_by', 'rejection_reason')
        }),
    )

    readonly_fields = ['application_date', 'approval_date']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'

    def is_approved(self, obj):
        if obj.user.is_vendor_approved:
            return format_html('<span style="color: green;">✓ Approved</span>')
        return format_html('<span style="color: red;">✗ Pending</span>')
    is_approved.short_description = 'Status'

    actions = ['approve_vendors', 'reject_vendors']

    def approve_vendors(self, request, queryset):
        for vendor in queryset:
            vendor.user.is_vendor_approved = True
            vendor.user.save()
            vendor.approved_by = request.user
            vendor.approval_date = timezone.now()
            vendor.save()
        self.message_user(request, f'{queryset.count()} vendors approved.')
    approve_vendors.short_description = 'Approve selected vendors'

    def reject_vendors(self, request, queryset):
        for vendor in queryset:
            vendor.user.is_vendor_approved = False
            vendor.user.save()
            vendor.approved_by = None
            vendor.approval_date = None
            vendor.save()
        self.message_user(request, f'{queryset.count()} vendors rejected.')
    reject_vendors.short_description = 'Reject selected vendors'


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Customer profile admin configuration."""

    list_display = ['user_email', 'newsletter_subscribed', 'created_at']
    list_filter = ['newsletter_subscribed', 'created_at']
    search_fields = ['user__email']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Address admin configuration."""

    list_display = [
        'user_email', 'type', 'first_name', 'last_name',
        'city', 'state', 'is_default'
    ]
    list_filter = ['type', 'is_default', 'country', 'state']
    search_fields = ['user__email', 'first_name', 'last_name', 'city']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
