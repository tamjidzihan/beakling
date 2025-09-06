"""Catalog filters."""

import django_filters
from django.db import models
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    """Product filter set."""

    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all())
    price_min = django_filters.NumberFilter(
        field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(
        field_name='price', lookup_expr='lte')
    age_min = django_filters.NumberFilter(
        field_name='age_min', lookup_expr='gte')
    age_max = django_filters.NumberFilter(
        field_name='age_max', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    on_sale = django_filters.BooleanFilter(method='filter_on_sale')
    rating_min = django_filters.NumberFilter(
        field_name='rating_avg', lookup_expr='gte')

    class Meta:
        model = Product
        fields = {
            'vendor': ['exact'],
            'tags': ['exact'],
            'is_featured': ['exact'],
        }

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(inventory__gt=0)
        return queryset

    def filter_on_sale(self, queryset, name, value):
        if value:
            return queryset.filter(
                sale_price__isnull=False,
                sale_price__lt=models.F('price')
            )
        return queryset
