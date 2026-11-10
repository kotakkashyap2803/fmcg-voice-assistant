from rest_framework import serializers
from decimal import Decimal

from .models import (
    Category,
    Brand,
    Product,
    ProductAlias,
    ProductVariant,
    Inventory,
    InventoryTransaction,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"


class ProductAliasSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAlias
        fields = ["id", "alias", "language"]


class ProductVariantSerializer(serializers.ModelSerializer):
    inventory_quantity = serializers.SerializerMethodField()
    reorder_level = serializers.SerializerMethodField()
    low_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id", "variant_name", "sku", "barcode",
            "pack_size", "unit", "mrp", "selling_price",
            "is_active", "inventory_quantity", "reorder_level",
            "low_stock"
        ]

    def get_inventory_quantity(self, obj):
        try:
            return obj.inventory.quantity_on_hand
        except Inventory.DoesNotExist:
            return 0

    def get_reorder_level(self, obj):
        try:
            return obj.inventory.reorder_level
        except Inventory.DoesNotExist:
            return 0

    def get_low_stock(self, obj):
        try:
            return obj.inventory.is_low_stock
        except Inventory.DoesNotExist:
            return True


class ProductSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(
        source="brand.name", read_only=True
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )
    aliases = ProductAliasSerializer(many=True, required=False)
    variants = ProductVariantSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id", "name", "product_code", "brand", "brand_name",
            "category", "category_name", "description",
            "is_active", "aliases", "variants",
            "created_at", "updated_at"
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        aliases_data = validated_data.pop("aliases", [])
        variants_data = validated_data.pop("variants", [])

        from django.db import transaction

        with transaction.atomic():
            product = Product.objects.create(**validated_data)

            for alias in aliases_data:
                ProductAlias.objects.create(
                    product=product, **alias
                )

            for variant in variants_data:
                ProductVariant.objects.create(
                    product=product, **variant
                )

        return product

    def update(self, instance, validated_data):
        aliases_data = validated_data.pop("aliases", None)
        variants_data = validated_data.pop("variants", None)

        from django.db import transaction

        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)

            instance.save()

            if aliases_data is not None:
                instance.aliases.all().delete()
                for alias in aliases_data:
                    ProductAlias.objects.create(
                        product=instance, **alias
                    )

            if variants_data is not None:
                # Existing variants are retained to protect inventory
                # and transaction history. Update by ID or create new.
                for variant_data in variants_data:
                    variant_id = variant_data.pop("id", None)

                    if variant_id:
                        variant = ProductVariant.objects.get(
                            id=variant_id, product=instance
                        )
                        for field, value in variant_data.items():
                            setattr(variant, field, value)
                        variant.save()
                    else:
                        ProductVariant.objects.create(
                            product=instance, **variant_data
                        )

        return instance


class InventorySerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(
        source="variant.product.name", read_only=True
    )
    variant_name = serializers.CharField(
        source="variant.variant_name", read_only=True
    )
    low_stock = serializers.BooleanField(
        source="is_low_stock", read_only=True
    )

    class Meta:
        model = Inventory
        fields = [
            "id", "variant", "sku", "product_name",
            "variant_name", "quantity_on_hand",
            "reorder_level", "low_stock", "updated_at"
        ]
        read_only_fields = [
            "variant", "quantity_on_hand", "updated_at"
        ]


class InventoryAdjustmentSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    transaction_type = serializers.ChoiceField(
        choices=InventoryTransaction.TransactionType.choices
    )
    quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal(0.001)
    )
    reason = serializers.CharField(max_length=255)
    reference = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )


class InventoryTransactionSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source="variant.sku", read_only=True)
    product_name = serializers.CharField(
        source="variant.product.name", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True, default=None
    )

    class Meta:
        model = InventoryTransaction
        fields = "__all__"