from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brands"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    product_code = models.CharField(max_length=50, unique=True)
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name="products"
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["brand", "category"]),
            models.Index(fields=["is_active", "name"]),
        ]

    def __str__(self):
        return f"{self.brand.name} - {self.name}"


class ProductAlias(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="aliases"
    )
    alias = models.CharField(max_length=200, unique=True, db_index=True)
    language = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_aliases"
        ordering = ["alias"]

    def __str__(self):
        return self.alias


class ProductVariant(models.Model):
    class Unit(models.TextChoices):
        GRAM = "G", "Gram"
        KILOGRAM = "KG", "Kilogram"
        MILLILITRE = "ML", "Millilitre"
        LITRE = "L", "Litre"
        PIECE = "PCS", "Piece"
        PACK = "PACK", "Pack"
        BOX = "BOX", "Box"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    variant_name = models.CharField(max_length=150)
    sku = models.CharField(max_length=60, unique=True)
    barcode = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    pack_size = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(0.001)]
    )
    unit = models.CharField(max_length=10, choices=Unit.choices)
    mrp = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_variants"
        ordering = ["product__name", "pack_size"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["barcode"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.variant_name}"


class Inventory(models.Model):
    variant = models.OneToOneField(
        ProductVariant, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity_on_hand = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        validators=[MinValueValidator(0)]
    )
    reorder_level = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        validators=[MinValueValidator(0)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory"

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.reorder_level

    def __str__(self):
        return f"{self.variant.sku}: {self.quantity_on_hand}"


class InventoryTransaction(models.Model):
    class TransactionType(models.TextChoices):
        STOCK_IN = "IN", "Stock In"
        STOCK_OUT = "OUT", "Stock Out"
        ADJUSTMENT = "ADJUSTMENT", "Stock Correction"

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="inventory_transactions"
    )
    transaction_type = models.CharField(
        max_length=20, choices=TransactionType.choices
    )
    quantity = models.DecimalField(
        max_digits=14, decimal_places=3,
        validators=[MinValueValidator(0.001)]
    )
    previous_quantity = models.DecimalField(
        max_digits=14, decimal_places=3
    )
    new_quantity = models.DecimalField(
        max_digits=14, decimal_places=3
    )
    reason = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["variant", "-created_at"]),
            models.Index(fields=["transaction_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.variant.sku} - {self.transaction_type} - {self.quantity}"