"""Custom adapters for django-allauth."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter."""

    def get_login_redirect_url(self, request):
        """Redirect to frontend after login."""
        return f"{settings.FRONTEND_URL}/dashboard"

    def get_signup_redirect_url(self, request):
        """Redirect to frontend after signup."""
        return f"{settings.FRONTEND_URL}/welcome"


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom social account adapter."""

    def get_connect_redirect_url(self, request, socialaccount):
        """Redirect after social account connection."""
        return f"{settings.FRONTEND_URL}/dashboard"

    def populate_user(self, request, sociallogin, data):
        """Populate user data from social login."""
        user = super().populate_user(request, sociallogin, data)
        
        # Set default role for social login users
        if not user.role:
            user.role = 'CUSTOMER'
            
        return user