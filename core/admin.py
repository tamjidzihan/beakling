from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseAdmin
from .models import *
# Register your models here.


@admin.register(User)
class UserAdmin(BaseAdmin):
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2","first_name","last_name","email"),
            },
        ),
    )