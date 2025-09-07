"""Catalog views."""

from rest_framework import serializers
from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, F
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from apps.common.permissions import IsVendorOrReadOnly, IsAdminOrReadOnly
from .models import Category, Tag, Product, Book, Toy, ProductImage, Review, Wishlist
from .serializers import (
    CategorySerializer, TagSerializer, ProductListSerializer, ProductDetailSerializer,
    BookSerializer, ToySerializer, BookListSerializer, ToyListSerializer,
    ProductImageSerializer, ReviewSerializer, WishlistSerializer, WishlistActionResponseSerializer, ProductSearchSerializer
)
from .filters import ProductFilter


@extend_schema(tags=['Categories'])
class CategoryListView(generics.ListCreateAPIView):
    """
    List and create product categories.

    Categories are used to organize products into logical groups (Books, Toys, etc.).
    Only admin users can create new categories.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sort_order', 'name', 'created_at']
    ordering = ['type', 'sort_order']

    @extend_schema(
        summary="List categories",
        description='Retrieve a list of product categories with optional filtering.',
        parameters=[
            OpenApiParameter(
                name='type',
                description='Filter by category type (BOOKS/TOYS)',
                required=False,
                type=str,
                enum=['BOOKS', 'TOYS']
            ),
            OpenApiParameter(
                name='show_all',
                description='Show all categories including subcategories',
                required=False,
                type=bool
            )
        ],
        responses={
            200: CategorySerializer(many=True),
            403: OpenApiResponse(description="Admin access required for creation")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create category",
        description="Create a new product category (Admin only).",
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Admin access required")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        category_type = self.request.query_params.get('type')
        if category_type:
            queryset = queryset.filter(type=category_type)

        show_all = self.request.query_params.get(
            'show_all', 'false').lower() == 'true'
        if not show_all:
            queryset = queryset.filter(parent__isnull=True)

        return queryset


@extend_schema(tags=['Categories'])
class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific category.
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'

    @extend_schema(
        summary="Get category details",
        description="Retrieve detailed information about a specific category.",
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description="Category not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update category",
        description="Update a category (Admin only).",
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Admin access required"),
            404: OpenApiResponse(description="Category not found")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Delete category",
        description="Delete a category (Admin only).",
        responses={
            204: OpenApiResponse(description="Category deleted successfully"),
            403: OpenApiResponse(description="Admin access required"),
            404: OpenApiResponse(description="Category not found")
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


@extend_schema(tags=['Tags'])
class TagListView(generics.ListCreateAPIView):
    """
    List and create product tags.

    Tags are used for categorizing and filtering products.
    Only admin users can create new tags.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    @extend_schema(
        summary="List tags",
        description="Retrieve a list of product tags with search functionality.",
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search tags by name',
                required=False,
                type=str
            )
        ],
        responses={
            200: TagSerializer(many=True),
            403: OpenApiResponse(description="Admin access required for creation")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create tag",
        description="Create a new product tag (Admin only).",
        responses={
            201: TagSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Admin access required")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['Products'])
class ProductListView(generics.ListAPIView):
    """
    Browse and search products with advanced filtering.

    Supports comprehensive filtering, searching, and sorting of products.
    Available to all users without authentication.
    """
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['title', 'description', 'sku']
    ordering_fields = ['created_at', 'price', 'rating_avg', 'title']
    ordering = ['-created_at']

    @extend_schema(
        summary="Browse products",
        description='Browse and search products with advanced filtering options.',
        parameters=[
            OpenApiParameter(
                name='query',
                description='Search query for product title, description, or SKU',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='min_price',
                description='Minimum price filter',
                required=False,
                type=float
            ),
            OpenApiParameter(
                name='max_price',
                description='Maximum price filter',
                required=False,
                type=float
            ),
            OpenApiParameter(
                name='min_age',
                description='Minimum age filter',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='max_age',
                description='Maximum age filter',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='in_stock_only',
                description='Show only products in stock',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='on_sale_only',
                description='Show only products on sale',
                required=False,
                type=bool
            ),
            OpenApiParameter(
                name='rating_min',
                description='Minimum rating filter (1-5)',
                required=False,
                type=float
            ),
            OpenApiParameter(
                name='vendor',
                description='Filter by vendor ID',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='category',
                description='Filter by category ID',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='tags',
                description='Filter by tag names (comma-separated)',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='sort_by',
                description='Sort results by field',
                required=False,
                type=str,
                enum=['created_at', 'price', 'rating_avg', 'title']
            )
        ],
        responses={
            200: ProductListSerializer(many=True),
            400: OpenApiResponse(description="Invalid filter parameters")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related(
            'category', 'vendor'
        ).prefetch_related('images', 'tags')

        search_params = ProductSearchSerializer(
            data=self.request.query_params)  # type: ignore
        if search_params.is_valid():
            data = search_params.validated_data

            # Text search
            if data.get('query'):  # type: ignore
                queryset = queryset.filter(
                    Q(title__icontains=data['query']) |  # type: ignore
                    Q(description__icontains=data['query']) |  # type: ignore
                    Q(sku__icontains=data['query'])  # type: ignore
                )

            # Price range
            if data.get('min_price'):  # type: ignore
                queryset = queryset.filter(
                    Q(price__gte=data['min_price']) |  # type: ignore
                    Q(sale_price__gte=data['min_price'])  # type: ignore
                )
            if data.get('max_price'):  # type: ignore
                queryset = queryset.filter(
                    Q(price__lte=data['max_price']) |  # type: ignore
                    Q(sale_price__lte=data['max_price'])  # type: ignore
                )

            # Age range
            if data.get('min_age'):  # type: ignore
                queryset = queryset.filter(
                    age_min__gte=data['min_age'])  # type: ignore
            if data.get('max_age'):  # type: ignore
                queryset = queryset.filter(
                    age_max__lte=data['max_age'])  # type: ignore

            # Stock filter
            if data.get('in_stock_only'):  # type: ignore
                queryset = queryset.filter(inventory__gt=0)

            # Sale filter
            if data.get('on_sale_only'):  # type: ignore
                queryset = queryset.filter(
                    sale_price__isnull=False,
                    sale_price__lt=F('price')
                )

            # Rating filter
            if data.get('rating_min'):  # type: ignore
                queryset = queryset.filter(
                    rating_avg__gte=data['rating_min'])  # type: ignore

            # Vendor filter
            if data.get('vendor'):  # type: ignore
                queryset = queryset.filter(
                    vendor_id=data['vendor'])  # type: ignore

            # Category filter
            if data.get('category'):  # type: ignore
                queryset = queryset.filter(
                    category_id=data['category'])  # type: ignore

            # Tags filter
            if data.get('tags'):  # type: ignore
                queryset = queryset.filter(
                    tags__name__in=data['tags']).distinct()  # type: ignore

            # Sorting
            if data.get('sort_by'):  # type: ignore
                queryset = queryset.order_by(data['sort_by'])  # type: ignore

        return queryset


@extend_schema(tags=['Products'])
class ProductDetailView(generics.RetrieveAPIView):
    """
    Get detailed information about a specific product.

    Includes complete product details, images, tags, and reviews.
    Available to all users without authentication.
    """
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Get product details",
        description="Retrieve complete details for a specific product including images, tags, and reviews.",
        responses={
            200: ProductDetailSerializer,
            404: OpenApiResponse(description="Product not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().select_related(
            'category', 'vendor'
        ).prefetch_related('images', 'tags', 'reviews__user')


@extend_schema(tags=['Books'])
class BookListCreateView(generics.ListCreateAPIView):
    """
    List and create books.

    Vendors can create new books and manage their own book listings.
    All users can browse books.
    """
    permission_classes = [IsVendorOrReadOnly]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'author', 'publisher', 'isbn_13']
    ordering_fields = ['created_at', 'price', 'rating_avg', 'title']
    ordering = ['-created_at']

    @extend_schema(
        summary="List books",
        description="Browse books with search and filtering options.",
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search books by title, author, publisher, or ISBN',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='ordering',
                description='Sort results',
                required=False,
                type=str,
                enum=['created_at', 'price', 'rating_avg', 'title']
            )
        ],
        responses={
            200: BookListSerializer(many=True),
            403: OpenApiResponse(description="Vendor access required for creation")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create book",
        description="Create a new book listing (Vendor only).",
        responses={
            201: BookSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Vendor access required")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Book.objects.filter(is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == 'VENDOR':  # type: ignore
            queryset = queryset.filter(vendor=self.request.user)
        return queryset.select_related('category', 'vendor').prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return BookListSerializer
        return BookSerializer

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)


@extend_schema(tags=['Books'])
class BookDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific book.

    Vendors can update or delete their own books. All users can view books.
    """
    serializer_class = BookSerializer
    permission_classes = [IsVendorOrReadOnly]

    @extend_schema(
        summary="Get book details",
        description="Retrieve complete details for a specific book.",
        responses={
            200: BookSerializer,
            404: OpenApiResponse(description="Book not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update book",
        description="Update a book listing (Vendor can only update their own books).",
        responses={
            200: BookSerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Vendor access required or not book owner"),
            404: OpenApiResponse(description="Book not found")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Delete book",
        description="Delete a book listing (Vendor can only delete their own books).",
        responses={
            204: OpenApiResponse(description="Book deleted successfully"),
            403: OpenApiResponse(description="Vendor access required or not book owner"),
            404: OpenApiResponse(description="Book not found")
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Book.objects.filter(is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == 'VENDOR':  # type: ignore
            queryset = queryset.filter(vendor=self.request.user)
        return queryset


@extend_schema(tags=['Toys'])
class ToyListCreateView(generics.ListCreateAPIView):
    """
    List and create toys.
    """
    permission_classes = [IsVendorOrReadOnly]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'brand', 'material']
    ordering_fields = ['created_at', 'price', 'rating_avg', 'title']
    ordering = ['-created_at']

    @extend_schema(
        summary="List toys",
        description="Browse toys with search and filtering options.",
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search toys by title, brand, or material',
                required=False,
                type=str
            ),
            OpenApiParameter(
                name='ordering',
                description='Sort results',
                required=False,
                type=str,
                enum=['created_at', 'price', 'rating_avg', 'title']
            )
        ],
        responses={
            200: ToyListSerializer(many=True),
            403: OpenApiResponse(description="Vendor access required for creation")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create toy",
        description="Create a new toy listing (Vendor only).",
        responses={
            201: ToySerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Vendor access required")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Toy.objects.filter(is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == 'VENDOR':  # type: ignore
            queryset = queryset.filter(vendor=self.request.user)
        return queryset.select_related('category', 'vendor').prefetch_related('images')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ToyListSerializer
        return ToySerializer

    def perform_create(self, serializer):
        serializer.save(vendor=self.request.user)


@extend_schema(tags=['Toys'])
class ToyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific toy.
    """
    serializer_class = ToySerializer
    permission_classes = [IsVendorOrReadOnly]

    @extend_schema(
        summary="Get toy details",
        description="Retrieve complete details for a specific toy.",
        responses={
            200: ToySerializer,
            404: OpenApiResponse(description="Toy not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update toy",
        description="Update a toy listing (Vendor can only update their own toys).",
        responses={
            200: ToySerializer,
            400: OpenApiResponse(description="Invalid input data"),
            403: OpenApiResponse(description="Vendor access required or not toy owner"),
            404: OpenApiResponse(description="Toy not found")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Delete toy",
        description="Delete a toy listing (Vendor can only delete their own toys).",
        responses={
            204: OpenApiResponse(description="Toy deleted successfully"),
            403: OpenApiResponse(description="Vendor access required or not toy owner"),
            404: OpenApiResponse(description="Toy not found")
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Toy.objects.filter(is_active=True)
        if self.request.user.is_authenticated and self.request.user.role == 'VENDOR':  # type: ignore
            queryset = queryset.filter(vendor=self.request.user)
        return queryset


@extend_schema(tags=['Products', 'Media'])
class ProductImageUploadView(generics.CreateAPIView):
    """
    Upload images for a product.
    """
    serializer_class = ProductImageSerializer
    permission_classes = [IsVendorOrReadOnly]

    @extend_schema(
        summary="Upload product image",
        description="Upload an image for a specific product.",
        responses={
            201: ProductImageSerializer,
            400: OpenApiResponse(description="Invalid image or product not found"),
            403: OpenApiResponse(description="Vendor access required or not product owner"),
            404: OpenApiResponse(description="Product not found")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']
        try:
            product = Product.objects.get(id=product_id)
            if product.vendor != self.request.user:
                raise PermissionError(
                    "You can only upload images for your own products.")
            serializer.save(product=product)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")


@extend_schema(tags=['Reviews'])
class ProductReviewListCreateView(generics.ListCreateAPIView):
    """
    List and create product reviews.
    """
    serializer_class = ReviewSerializer
    queryset = Review.objects.none()

    @extend_schema(
        summary="List product reviews",
        description="Retrieve all reviews for a specific product.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                description='ID of the product to get reviews for',
                required=True,
                type=int,
                location=OpenApiParameter.PATH
            )
        ],
        responses={
            200: ReviewSerializer(many=True),
            404: OpenApiResponse(description="Product not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create product review",
        description="Create a new review for a product.",
        parameters=[
            OpenApiParameter(
                name='product_id',
                description='ID of the product to review',
                required=True,
                type=int,
                location=OpenApiParameter.PATH
            )
        ],
        responses={
            201: ReviewSerializer,
            400: OpenApiResponse(description="Invalid review data or already reviewed"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Product not found")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return Review.objects.filter(product_id=product_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['product_id'] = self.kwargs['product_id']
        return context


@extend_schema(tags=['Wishlist'])
class WishlistListView(generics.ListAPIView):
    """
    Get user's wishlist items.
    """
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    queryset = Wishlist.objects.none()

    @extend_schema(
        summary="Get wishlist",
        description="Retrieve all items in the authenticated user's wishlist.",
        responses={
            200: WishlistSerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related('product')


@extend_schema(
    tags=['Wishlist'],
    summary="Add to wishlist",
    description="Add a product to the user's wishlist.",
    parameters=[
        OpenApiParameter(
            name='product_id',
            description='ID of the product to add',
            required=True,
            type=int,
            location=OpenApiParameter.PATH
        )
    ],
    responses={
        200: WishlistActionResponseSerializer,
        201: WishlistActionResponseSerializer,
        404: OpenApiResponse(description="Product not found or not in wishlist")
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_wishlist(request, product_id):
    """
    Add a product to the user's wishlist.
    """
    try:
        product = Product.objects.get(id=product_id, is_active=True)
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if created:
            response_data = {
                'message': 'Product added to wishlist.',
                'data': WishlistSerializer(wishlist_item).data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            response_data = {
                'message': 'Product already in wishlist.',
                'data': WishlistSerializer(wishlist_item).data
            }
            return Response(response_data)

    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=['Wishlist'],
    summary="Remove from wishlist",
    description="Remove a product from the user's wishlist.",
    parameters=[
        OpenApiParameter(
            name='product_id',
            description='ID of the product to remove',
            required=True,
            type=int,
            location=OpenApiParameter.PATH
        )
    ],
    responses={
        200: WishlistActionResponseSerializer,
        404: OpenApiResponse(description="Product not in wishlist")
    }
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_wishlist(request, product_id):
    """
    Remove a product from the user's wishlist.
    """
    try:
        wishlist_item = Wishlist.objects.get(
            user=request.user,
            product_id=product_id
        )
        wishlist_data = WishlistSerializer(wishlist_item).data
        wishlist_item.delete()

        response_data = {
            'message': 'Product removed from wishlist.',
            'data': wishlist_data  # Include the deleted item data
        }
        return Response(response_data)

    except Wishlist.DoesNotExist:
        return Response(
            {'error': 'Product not in wishlist.'},
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=['Search Suggestions'],
    summary="Get search suggestions",
    description="Get autocomplete suggestions for search queries.",
    parameters=[
        OpenApiParameter(
            name='q',
            description='Search query (min 2 characters)',
            required=True,
            type=str
        )
    ],
    responses={
        400: OpenApiResponse(description="Query too short")
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_suggestions(request):
    """Get search suggestions."""
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return Response([])

    # Get product title suggestions
    products = Product.objects.filter(
        title__icontains=query,
        is_active=True
    ).values_list('title', flat=True)[:5]

    # Get tag suggestions
    tags = Tag.objects.filter(
        name__icontains=query
    ).values_list('name', flat=True)[:5]

    # Get author suggestions (for books)
    authors = Book.objects.filter(
        author__icontains=query,
        is_active=True
    ).values_list('author', flat=True).distinct()[:3]

    # Get brand suggestions (for toys)
    brands = Toy.objects.filter(
        brand__icontains=query,
        is_active=True
    ).values_list('brand', flat=True).distinct()[:3]

    suggestions = list(products) + list(tags) + list(authors) + list(brands)
    return Response(suggestions[:10])


@extend_schema(
    tags=['Products'],
    summary="Get featured products",
    description="Returns a curated list of featured products for display on homepage.",
    responses={
        200: ProductListSerializer,
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def featured_products(request):
    """
    Get featured products.

    Returns a curated list of featured products for display on homepage.
    Available to all users without authentication.
    """
    products = Product.objects.filter(
        is_featured=True,
        is_active=True
    ).select_related('category', 'vendor').prefetch_related('images')[:8]

    serializer = ProductListSerializer(
        products, many=True, context={'request': request})
    return Response(serializer.data)
