from django.contrib import admin
from .models import Category, Product,Events

#register
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title','arthur' ,'catagory','slug', 'price','featureproduct','rating','image', 'created']
    # autocomplete_fields = ['catagory']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price','featureproduct']
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 50


@admin.register(Events)
class EventsAdmin(admin.ModelAdmin):
    list_display = ['event_name','event_time']
    list_editable = ['event_time']