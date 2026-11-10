from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import (
    Category,
    Brand,
    Product,
    ProductAlias,
    ProductVariant,
    Inventory,
    InventoryTransaction,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


class ProductAliasInline(admin.TabularInline):
    model = ProductAlias
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "product_code", "brand", "category", "is_active"
    )
    search_fields = ("name", "product_code", "brand__name")
    list_filter = ("brand", "category", "is_active")
    inlines = [ProductAliasInline, ProductVariantInline]


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "variant", "quantity_on_hand", "reorder_level", "updated_at"
    )
    search_fields = (
        "variant__sku", "variant__product__name"
    )
    list_filter = ("variant__product__brand",)


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "variant", "transaction_type", "quantity",
        "previous_quantity", "new_quantity", "created_at"
    )
    search_fields = ("variant__sku", "reason", "reference")
    list_filter = ("transaction_type", "created_at")
    readonly_fields = (
        "variant", "transaction_type", "quantity",
        "previous_quantity", "new_quantity", "reason",
        "reference", "created_by", "created_at"
    )