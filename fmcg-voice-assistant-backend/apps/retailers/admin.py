from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Retailer, RetailerContact


class RetailerContactInline(admin.TabularInline):

    model = RetailerContact

    extra = 1


@admin.register(Retailer)
class RetailerAdmin(admin.ModelAdmin):

    list_display = [
        "retailer_code",
        "name",
        "shop_name",
        "primary_phone",
        "territory",
        "business_status",
    ]

    list_filter = [
        "retailer_type",
        "business_status",
        "territory",
        "state",
    ]

    search_fields = [
        "retailer_code",
        "name",
        "shop_name",
        "primary_phone",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]

    inlines = [RetailerContactInline]


@admin.register(RetailerContact)
class RetailerContactAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "phone",
        "retailer",
        "contact_type",
        "is_primary",
    ]

    search_fields = [
        "name",
        "phone",
        "retailer__shop_name",
    ]