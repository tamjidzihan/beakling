from django.contrib import admin
from .models import Category,Books,Events

#register
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Books)
class BooksAdmin(admin.ModelAdmin):
    list_display = ['title','arthur' ,'catagory','slug', 'price','increased_price','featurebook','rating','created']
    # autocomplete_fields = ['catagory']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price','featurebook','increased_price']
    prepopulated_fields = {'slug': ('title',)}
    list_per_page = 50


@admin.register(Events)
class EventsAdmin(admin.ModelAdmin):
    list_display = ['event_name','event_time']
    list_editable = ['event_time']