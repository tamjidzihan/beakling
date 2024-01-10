from django.urls import path
from . import views

app_name = 'order'


urlpatterns = [
    path('add-to-cart/<int:pk>/',views.add_to_cart,name='add-to-cart'),
    path('cart-view/',view=views.car_view,name='cart-view'),
    path('remove-cart-item/<int:pk>',views.remove_cart_item,name='remove-cart-item'),
    path('increase-quantity/<int:pk>',views.increase_cart_item,name='increase-quantity'),
    path('decrease-quantity/<int:pk>',views.decrease_cart_item,name='decrease-quantity'),
]