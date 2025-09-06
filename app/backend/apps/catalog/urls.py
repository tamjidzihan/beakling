"""Catalog URLs."""

from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    
    # Tags
    path('tags/', views.TagListView.as_view(), name='tag_list'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/featured/', views.featured_products, name='featured_products'),
    path('products/search/suggestions/', views.search_suggestions, name='search_suggestions'),
    
    # Books
    path('books/', views.BookListCreateView.as_view(), name='book_list'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    
    # Toys
    path('toys/', views.ToyListCreateView.as_view(), name='toy_list'),
    path('toys/<int:pk>/', views.ToyDetailView.as_view(), name='toy_detail'),
    
    # Product Images
    path('products/<int:product_id>/images/', views.ProductImageUploadView.as_view(), name='product_image_upload'),
    
    # Reviews
    path('products/<int:product_id>/reviews/', views.ProductReviewListCreateView.as_view(), name='product_reviews'),
    
    # Wishlist
    path('wishlist/', views.WishlistListView.as_view(), name='wishlist_list'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
]