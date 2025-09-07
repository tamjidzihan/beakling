"""Catalog serializers."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from django.db.models import Q
from apps.common.serializers import TimestampedSerializer, DynamicFieldsSerializer
from .models import Category, Tag, Product, Book, Toy, ProductImage, Review, Wishlist


class CategorySerializer(TimestampedSerializer):
    """Category serializer."""

    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'type', 'image',
            'is_active', 'sort_order', 'children', 'product_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.filter(is_active=True), many=True).data
        return []

    @extend_schema_field(serializers.IntegerField())
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class TagSerializer(serializers.ModelSerializer):
    """Tag serializer."""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'color']


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer."""

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'sort_order']
        read_only_fields = ['id']


class ProductListSerializer(TimestampedSerializer, DynamicFieldsSerializer):
    """Product list serializer with minimal fields."""

    category_name = serializers.CharField(
        source='category.name', read_only=True)
    vendor_name = serializers.CharField(
        source='vendor.full_name', read_only=True)
    main_image = serializers.SerializerMethodField()
    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.FloatField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    age_range_display = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'title', 'price', 'sale_price', 'current_price',
            'inventory', 'category_name', 'vendor_name', 'main_image',
            'is_on_sale', 'discount_percentage', 'is_in_stock',
            'age_range_display', 'rating_avg', 'rating_count',
            'is_featured', 'created_at', 'updated_at'
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_main_image(self, obj):
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        return None


class ProductDetailSerializer(TimestampedSerializer):
    """Product detail serializer with all fields."""

    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    vendor_name = serializers.CharField(
        source='vendor.full_name', read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    images = ProductImageSerializer(many=True, read_only=True)
    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.FloatField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    age_range_display = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'title', 'description', 'price', 'sale_price',
            'current_price', 'inventory', 'category', 'category_id',
            'vendor_name', 'tags', 'tag_ids', 'age_min', 'age_max',
            'age_range_display', 'is_active', 'is_featured', 'rating_avg',
            'rating_count', 'is_on_sale', 'discount_percentage', 'is_in_stock',
            'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'vendor_name', 'created_at', 'updated_at']

    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        product = super().create(validated_data)
        if tag_ids:
            product.tags.set(tag_ids)
        return product

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)
        product = super().update(instance, validated_data)
        if tag_ids is not None:
            product.tags.set(tag_ids)
        return product


class BookSerializer(ProductDetailSerializer):
    """Book serializer."""

    class Meta(ProductDetailSerializer.Meta):
        model = Book
        fields = ProductDetailSerializer.Meta.fields + [
            'author', 'publisher', 'isbn_13', 'pages', 'language', 'publication_date'
        ]

    def validate_category_id(self, value):
        from apps.common.utils import Constants
        try:
            category = Category.objects.get(id=value)
            if category.type != Constants.BOOKS:
                raise serializers.ValidationError(
                    "Category must be of type BOOKS.")
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category not found.")
        return value


class ToySerializer(ProductDetailSerializer):
    """Toy serializer."""

    class Meta(ProductDetailSerializer.Meta):
        model = Toy
        fields = ProductDetailSerializer.Meta.fields + [
            'brand', 'material', 'safety_notes', 'dimensions', 'weight'
        ]

    def validate_category_id(self, value):
        from apps.common.utils import Constants
        try:
            category = Category.objects.get(id=value)
            if category.type != Constants.TOYS:
                raise serializers.ValidationError(
                    "Category must be of type TOYS.")
        except Category.DoesNotExist:
            raise serializers.ValidationError("Category not found.")
        return value


class BookListSerializer(ProductListSerializer):
    """Book list serializer."""

    author = serializers.CharField(read_only=True)

    class Meta(ProductListSerializer.Meta):
        model = Book
        fields = ProductListSerializer.Meta.fields + ['author']


class ToyListSerializer(ProductListSerializer):
    """Toy list serializer."""

    brand = serializers.CharField(read_only=True)

    class Meta(ProductListSerializer.Meta):
        model = Toy
        fields = ProductListSerializer.Meta.fields + ['brand']


class ReviewSerializer(TimestampedSerializer):
    """Review serializer."""

    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'rating', 'title', 'content', 'user_name', 'user_avatar',
            'is_verified_purchase', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_name',
                            'user_avatar', 'created_at', 'updated_at']

    def create(self, validated_data):
        user = self.context['request'].user
        product_id = self.context['product_id']

        # Replace create with update_or_create
        review, created = Review.objects.update_or_create(
            user=user,
            product_id=product_id,
            defaults=validated_data
        )
        return review


class WishlistSerializer(TimestampedSerializer):
    """Wishlist serializer."""

    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'created_at']
        read_only_fields = ['id', 'created_at']

# Add to your existing serializers.py


class WishlistActionResponseSerializer(serializers.Serializer):
    """Serializer for wishlist action responses."""
    message = serializers.CharField()
    error = serializers.CharField(required=False, allow_blank=True)


class ProductSearchSerializer(serializers.Serializer):
    """Product search parameters serializer."""

    query = serializers.CharField(required=False, allow_blank=True)
    category = serializers.IntegerField(required=False)
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False)
    min_age = serializers.IntegerField(required=False)
    max_age = serializers.IntegerField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    in_stock_only = serializers.BooleanField(required=False, default=False)
    on_sale_only = serializers.BooleanField(required=False, default=False)
    vendor = serializers.IntegerField(required=False)
    rating_min = serializers.DecimalField(
        max_digits=3, decimal_places=2, required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            'created_at', '-created_at', 'price', '-price',
            'rating_avg', '-rating_avg', 'title', '-title'
        ],
        required=False,
        default='-created_at'
    )
