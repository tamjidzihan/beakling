"""Catalog models."""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from apps.common.models import BaseModel, OrderedModel
from apps.common.utils import Constants, validate_image_file

User = get_user_model()


class Category(BaseModel, OrderedModel):
    """Product category model."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    type = models.CharField(
        max_length=20,
        choices=Constants.CATEGORY_TYPE_CHOICES,
        default=Constants.BOOKS
    )
    image = models.ImageField(
        upload_to='categories/',
        null=True,
        blank=True,
        validators=[validate_image_file]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['type', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.type})"

    @property
    def full_name(self):
        """Get full category path."""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name


class Tag(models.Model):
    """Product tag model."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6B7280')  # Hex color

    def __str__(self):
        return self.name


class Product(BaseModel):
    """Base product model."""

    sku = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    inventory = models.PositiveIntegerField(default=0)
    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='products'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )
    tags = models.ManyToManyField(Tag, blank=True)

    # Age range
    age_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(18)]
    )
    age_max = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(18)]
    )

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Rating
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00  # type: ignore
    )
    rating_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['rating_avg']),
        ]

    def __str__(self):
        return self.title

    @property
    def current_price(self):
        """Get current selling price."""
        return self.sale_price if self.sale_price else self.price

    @property
    def is_on_sale(self):
        """Check if product is on sale."""
        return self.sale_price and self.sale_price < self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage."""
        if self.is_on_sale and self.price is not None and self.sale_price is not None:
            return round(((self.price - self.sale_price) / self.price) * 100, 2)
        return 0

    @property
    def is_in_stock(self):
        """Check if product is in stock."""
        return self.inventory > 0

    @property
    def age_range_display(self):
        """Get formatted age range."""
        if self.age_min is not None and self.age_max is not None:
            return f"{self.age_min}-{self.age_max} years"
        elif self.age_min is not None:
            return f"{self.age_min}+ years"
        return "All ages"


class Book(Product):
    """Book product model."""

    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    isbn_13 = models.CharField(
        max_length=13, unique=True, null=True, blank=True)
    pages = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, default='English')
    publication_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'

    def save(self, *args, **kwargs):
        # Ensure category type is BOOKS
        if self.category and self.category.type != Constants.BOOKS:
            raise ValueError("Book must be assigned to a BOOKS category.")
        super().save(*args, **kwargs)


class Toy(Product):
    """Toy product model."""

    brand = models.CharField(max_length=100)
    material = models.CharField(max_length=255, blank=True)
    safety_notes = models.TextField(blank=True)
    dimensions = models.CharField(
        max_length=100, blank=True)  # e.g., "10x5x3 inches"
    weight = models.CharField(max_length=50, blank=True)  # e.g., "1.2 lbs"

    class Meta:
        verbose_name = 'Toy'
        verbose_name_plural = 'Toys'

    def save(self, *args, **kwargs):
        # Ensure category type is TOYS
        if self.category and self.category.type != Constants.TOYS:
            raise ValueError("Toy must be assigned to a TOYS category.")
        super().save(*args, **kwargs)


class ProductImage(OrderedModel):
    """Product image model."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='products/',
        validators=[validate_image_file]
    )
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.product.title} - Image {self.sort_order}"

    def save(self, *args, **kwargs):
        if not self.alt_text:
            self.alt_text = f"{self.product.title} image"
        super().save(*args, **kwargs)


class Review(BaseModel):
    """Product review model."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)

    class Meta:
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.title} - {self.rating}★ by {self.user.email}"

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)

        # Update product rating when review is saved
        if is_new:
            self.update_product_rating()

    def update_product_rating(self):
        """Update product's average rating."""
        from django.db.models import Avg, Count

        rating_data = Review.objects.filter(product=self.product).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )

        self.product.rating_avg = rating_data['avg_rating'] or 0
        self.product.rating_count = rating_data['count'] or 0
        self.product.save(update_fields=['rating_avg', 'rating_count'])


class Wishlist(BaseModel):
    """User wishlist model."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )

    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.title}"
