from django.contrib import admin
from . import models
# Register your models here.




@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user','full_name','email','date_of_birth','phone','address','country','city','zipcode','phone']
    ordering = ['full_name']
    search_fields = ['full_name__istartswith']
    list_per_page = 50


