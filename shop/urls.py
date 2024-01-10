from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.index, name='index'),
    path('books/', views.book_list, name='books'),
    path('about/',views.about,name='about'),
    path('terms-and-conditions/',views.termsandconditions,name='terms-and-conditions'),
    # path('<slug:category_slug>/', views.book_list, name='book_list_by_category'),
    path('<int:id>/<slug:slug>/', views.book_detail, name='book_detail'),

    path('products/', views.product_list, name='products'),

]   