from django.contrib import admin
from .models import Cart,Order

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'item', 'quantity', 'total_price', 'purchased', 'created', 'update']
    list_filter = ['purchased', 'created', 'update']
    list_editable = ['purchased']
    search_fields = ['user__username', 'item__title']

    def total_price(self, obj):
        return obj.get_total_price()

    total_price.short_description = 'Total Price'
    


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'ordered','calculate_totals_price', 'created', 'paymentID', 'orderID']
    list_filter = ['ordered', 'created']
    search_fields = ['user__username', 'paymentID', 'orderID']
    readonly_fields = ['created']

    fieldsets = [
        ('Order Information', {'fields': ['user', 'ordered', 'created', 'paymentID', 'orderID']}),
        ('Order Items', {'fields': ['orderitems']}),
    ]

    filter_horizontal = ('orderitems',)

    def calculate_totals_price(self, obj):
        return obj.calculate_totals()
    

    
# admin.site.register(Order)