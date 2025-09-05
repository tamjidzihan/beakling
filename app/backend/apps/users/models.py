"""User models."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.models import TimestampedModel
from apps.common.utils import Constants, validate_image_file


class User(AbstractUser, TimestampedModel):
    """Custom user model."""

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Constants.USER_ROLE_CHOICES,
        default=Constants.CUSTOMER
    )
    is_vendor_approved = models.BooleanField(default=False)
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        validators=[validate_image_file]
    )
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Remove username field
    username = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == Constants.ADMIN or self.is_superuser

    @property
    def is_vendor(self):
        return self.role == Constants.VENDOR and self.is_vendor_approved

    @property
    def is_customer(self):
        return self.role == Constants.CUSTOMER

    def save(self, *args, **kwargs):
        # Auto-approve admin users
        if self.role == Constants.ADMIN:
            self.is_vendor_approved = True
        super().save(*args, **kwargs)


class VendorProfile(TimestampedModel):
    """Extended profile for vendor users."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vendor_profile'
    )
    business_name = models.CharField(max_length=255)
    business_description = models.TextField(blank=True)
    business_address = models.TextField()
    business_phone = models.CharField(max_length=20)
    business_email = models.EmailField()
    tax_id = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)

    # Approval fields
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_vendors'
    )
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"{self.business_name} - {self.user.email}"


class CustomerProfile(TimestampedModel):
    """Extended profile for customer users."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    preferences = models.JSONField(default=dict, blank=True)
    newsletter_subscribed = models.BooleanField(default=True)

    def __str__(self):
        return f"Customer: {self.user.email}"


class Address(TimestampedModel):
    """User address model."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses'
    )
    type = models.CharField(
        max_length=20,
        choices=[
            ('billing', 'Billing'),
            ('shipping', 'Shipping'),
        ],
        default='shipping'
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    company = models.CharField(max_length=100, blank=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.city}, {self.state}"

    def save(self, *args, **kwargs):
        # Ensure only one default address per user per type
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                type=self.type,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)
