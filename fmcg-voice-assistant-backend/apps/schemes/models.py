from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.catalogue.models import ProductVariant


class Scheme(models.Model):

    class SchemeType(models.TextChoices):
        BUY_X_GET_Y = "BUY_X_GET_Y", "Buy X Get Y"
        PERCENTAGE = "PERCENTAGE", "Percentage Discount"
        QUANTITY_SLAB = "QUANTITY_SLAB", "Quantity Slab"
        COMBO = "COMBO", "Combo Offer"

    name = models.CharField(max_length=150)
    scheme_code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    scheme_type = models.CharField(
        max_length=20,
        choices=SchemeType.choices
    )

    applicable_variants = models.ManyToManyField(
        ProductVariant,
        related_name="schemes",
        blank=True
    )

    # Buy X Get Y
    buy_quantity = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    free_quantity = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # Percentage discount
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )

    min_quantity = models.PositiveIntegerField(default=1)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)
    is_combinable = models.BooleanField(default=False)

    max_discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "schemes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "start_date", "end_date"]),
            models.Index(fields=["scheme_type"]),
        ]

    def __str__(self):
        return f"{self.scheme_code} - {self.name}"


class SchemeSlab(models.Model):
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.CASCADE,
        related_name="slabs"
    )

    min_quantity = models.PositiveIntegerField()
    max_quantity = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )

    class Meta:
        db_table = "scheme_slabs"
        ordering = ["min_quantity"]
        unique_together = ("scheme", "min_quantity")

    def __str__(self):
        return (
            f"{self.scheme.name}: "
            f"{self.min_quantity}+ = {self.discount_percentage}%"
        )