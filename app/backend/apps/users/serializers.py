"""User serializers."""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from apps.common.serializers import TimestampedSerializer
from .models import User, VendorProfile, CustomerProfile, Address


class UserSerializer(TimestampedSerializer):
    """User serializer for general use."""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'is_vendor_approved', 'avatar', 'phone', 'date_of_birth',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'role', 'is_vendor_approved', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer."""
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'password', 'password_confirm',
            'phone', 'date_of_birth'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Password change serializer."""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not authenticate(username=user.email, password=value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class VendorProfileSerializer(TimestampedSerializer):
    """Vendor profile serializer."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'user_email', 'user_name', 'business_name',
            'business_description', 'business_address', 'business_phone',
            'business_email', 'tax_id', 'website', 'application_date',
            'approval_date', 'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'application_date', 'approval_date', 'rejection_reason',
            'created_at', 'updated_at'
        ]


class VendorApplicationSerializer(serializers.ModelSerializer):
    """Vendor application serializer."""
    
    class Meta:
        model = VendorProfile
        fields = [
            'business_name', 'business_description', 'business_address',
            'business_phone', 'business_email', 'tax_id', 'website'
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        # Update user role to VENDOR
        user.role = 'VENDOR'
        user.save()
        
        # Create vendor profile
        vendor_profile = VendorProfile.objects.create(
            user=user,
            **validated_data
        )
        return vendor_profile


class CustomerProfileSerializer(TimestampedSerializer):
    """Customer profile serializer."""
    
    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'preferences', 'newsletter_subscribed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AddressSerializer(TimestampedSerializer):
    """Address serializer."""
    
    class Meta:
        model = Address
        fields = [
            'id', 'type', 'first_name', 'last_name', 'company',
            'address_line_1', 'address_line_2', 'city', 'state',
            'postal_code', 'country', 'phone', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class GoogleAuthSerializer(serializers.Serializer):
    """Google authentication serializer."""
    
    access_token = serializers.CharField(required=True)

    def validate_access_token(self, value):
        # This would be implemented with Google's OAuth verification
        # For now, it's a placeholder
        return value