"""Catalog admin configuration."""

from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tag, Product, Book, Toy, ProductImage, Review, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category admin configuration."""

    list_display = ['name', 'type', 'parent',
                    'product_count', 'sort_order', 'is_active']
    list_filter = ['type', 'is_active', 'parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['sort_order', 'is_active']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Tag admin configuration."""

    list_display = ['name', 'color', 'product_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.product_set.count()
    product_count.short_description = 'Products'


class ProductImageInline(admin.TabularInline):
    """Product image inline."""
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'sort_order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Product admin configuration."""

    list_display = [
        'title', 'vendor', 'category', 'price', 'sale_price',
        'inventory', 'rating_display', 'is_active', 'created_at'
    ]
    list_filter = ['category', 'vendor',
                   'is_active', 'is_featured', 'created_at']
    search_fields = ['title', 'sku', 'description']
    readonly_fields = ['rating_avg',
                       'rating_count', 'created_at', 'updated_at']
    filter_horizontal = ['tags']
    inlines = [ProductImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('sku', 'title', 'description', 'vendor', 'category')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'sale_price', 'inventory')
        }),
        ('Classification', {
            'fields': ('tags', 'age_min', 'age_max')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Rating', {
            'fields': ('rating_avg', 'rating_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def rating_display(self, obj):
        if obj.rating_count > 0:
            return f"{obj.rating_avg:.1f} ⭐ ({obj.rating_count})"
        return "No ratings"
    rating_display.short_description = 'Rating'


@admin.register(Book)
class BookAdmin(ProductAdmin):
    """Book admin configuration."""

    list_display = list(ProductAdmin.list_display) + ['author', 'publisher']
    search_fields = list(ProductAdmin.search_fields) + \
        ['author', 'publisher', 'isbn_13']

    fieldsets = tuple(
        list(ProductAdmin.fieldsets[:2]) +
        [
            ('Book Details', {
                'fields': ('author', 'publisher', 'isbn_13', 'pages', 'language', 'publication_date')
            }),
        ] +
        list(ProductAdmin.fieldsets[2:])
    )


@admin.register(Toy)
class ToyAdmin(ProductAdmin):
    """Toy admin configuration."""

    list_display = list(ProductAdmin.list_display + ['brand'])  # type: ignore
    search_fields = list(ProductAdmin.search_fields +
                         ['brand', 'material'])  # type: ignore

    fieldsets = ProductAdmin.fieldsets[:2] + (
        ('Toy Details', {
            'fields': ('brand', 'material', 'safety_notes', 'dimensions', 'weight')
        }),
    ) + ProductAdmin.fieldsets[2:]  # type: ignore


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """Product image admin configuration."""

    list_display = ['product_title', 'image_preview', 'sort_order']
    list_filter = ['product__category']
    search_fields = ['product__title', 'alt_text']

    def product_title(self, obj):
        return obj.product.title
    product_title.short_description = 'Product'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Review admin configuration."""

    list_display = ['product_title', 'user_email', 'rating',
                    'title', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['product__title', 'user__email', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']

    def product_title(self, obj):
        return obj.product.title
    product_title.short_description = 'Product'

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    """Wishlist admin configuration."""

    list_display = ['user_email', 'product_title', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'product__title']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def product_title(self, obj):
        return obj.product.title
    product_title.short_description = 'Product'
