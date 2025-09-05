from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """Abstract base class for models that need timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base class for models that need soft delete functionality."""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """Soft delete the model."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self, *args, **kwargs):
        """Permanently delete the model."""
        super().delete(*args, **kwargs)

    def restore(self):
        """Restore a soft-deleted model."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class BaseModel(TimestampedModel, SoftDeleteModel):
    """Base model with timestamps and soft delete."""

    class Meta:
        abstract = True


class OrderedModel(models.Model):
    """Abstract base class for models that need ordering."""
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['sort_order']
