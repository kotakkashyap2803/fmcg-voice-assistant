from django.db import models

# Create your models here.
import uuid

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from decimal import Decimal


class Order(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False
    )

    retailer = models.ForeignKey(
        "retailers.Retailer",
        on_delete=models.PROTECT,
        related_name="orders"
    )

    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_orders"
    )

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_orders"
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["retailer", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = (
                f"ORD-{timezone.now():%Y%m%d}-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    # Snapshot fields: preserve the price at the time of ordering.
    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))]
    )

    free_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    mrp = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_items"
        ordering = ["id"]

    @property
    def total_units(self):
        return self.quantity + self.free_quantity

    def __str__(self):
        return f"{self.order.order_number} - {self.sku}"


class OrderItemScheme(models.Model):

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="applied_schemes"
    )

    scheme = models.ForeignKey(
        "schemes.Scheme",
        on_delete=models.PROTECT,
        related_name="order_applications"
    )

    # Snapshot scheme details so historical orders remain accurate.
    scheme_name = models.CharField(max_length=255)
    scheme_code = models.CharField(max_length=100)
    scheme_type = models.CharField(max_length=30)

    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    free_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_item_schemes"

    def __str__(self):
        return f"{self.scheme_code} - {self.order_item.order.order_number}"


class OrderStatusHistory(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history"
    )

    previous_status = models.CharField(
        max_length=15,
        blank=True,
        default=""
    )

    new_status = models.CharField(max_length=15)

    remarks = models.TextField(blank=True, default="")

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_status_history"
        ordering = ["created_at"]

    def __str__(self):
        return (
            f"{self.order.order_number}: "
            f"{self.previous_status} -> {self.new_status}"
        )