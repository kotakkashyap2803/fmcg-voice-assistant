from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from .models import (
    Product,
    ProductVariant,
    Inventory,
    InventoryTransaction,
)


class ProductService:

    @staticmethod
    def search_products(query):
        query = (query or "").strip()

        products = Product.objects.filter(
            is_active=True
        ).select_related("brand", "category").prefetch_related(
            "aliases", "variants"
        )

        if not query:
            return products

        from django.db.models import Q

        return products.filter(
            Q(name__icontains=query)
            | Q(product_code__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(aliases__alias__icontains=query)
            | Q(variants__sku__icontains=query)
            | Q(variants__barcode__icontains=query)
        ).distinct()

    @staticmethod
    def get_variant(variant_id):
        try:
            return ProductVariant.objects.select_related(
                "product", "product__brand", "product__category"
            ).get(pk=variant_id, is_active=True, product__is_active=True)
        except ProductVariant.DoesNotExist:
            raise NotFound("Product variant not found.")

    @staticmethod
    def get_inventory(variant_id):
        variant = ProductService.get_variant(variant_id)

        inventory, _ = Inventory.objects.get_or_create(
            variant=variant
        )
        return inventory


class InventoryService:

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        variant_id,
        transaction_type,
        quantity,
        reason,
        user=None,
        reference=""
    ):
        try:
            quantity = Decimal(str(quantity))
        except Exception:
            raise ValidationError({"quantity": "Enter a valid number."})

        if not quantity.is_finite() or quantity <= 0:
            raise ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )

        allowed_types = [
            InventoryTransaction.TransactionType.STOCK_IN,
            InventoryTransaction.TransactionType.STOCK_OUT,
            InventoryTransaction.TransactionType.ADJUSTMENT,
        ]

        if transaction_type not in allowed_types:
            raise ValidationError(
                {"transaction_type": "Invalid stock transaction type."}
            )

        if not reason or not reason.strip():
            raise ValidationError({"reason": "A reason is required."})

        variant = ProductService.get_variant(variant_id)

        inventory, _ = Inventory.objects.get_or_create(
            variant=variant
        )

        # Lock the inventory row to prevent concurrent stock changes.
        inventory = Inventory.objects.select_for_update().get(
            pk=inventory.pk
        )

        previous = inventory.quantity_on_hand

        if transaction_type == InventoryTransaction.TransactionType.STOCK_IN:
            new_quantity = previous + quantity

        elif transaction_type == InventoryTransaction.TransactionType.STOCK_OUT:
            new_quantity = previous - quantity

            if new_quantity < 0:
                raise ValidationError({
                    "quantity": (
                        f"Insufficient stock. Available: {previous}"
                    )
                })

        else:
            # ADJUSTMENT sets the actual stock to the supplied quantity.
            new_quantity = quantity

        inventory.quantity_on_hand = new_quantity
        inventory.save(update_fields=[
            "quantity_on_hand", "updated_at"
        ])

        stock_transaction = InventoryTransaction.objects.create(
            variant=variant,
            transaction_type=transaction_type,
            quantity=quantity,
            previous_quantity=previous,
            new_quantity=new_quantity,
            reason=reason.strip(),
            reference=reference,
            created_by=user
        )

        return {
            "inventory": inventory,
            "transaction": stock_transaction
        }