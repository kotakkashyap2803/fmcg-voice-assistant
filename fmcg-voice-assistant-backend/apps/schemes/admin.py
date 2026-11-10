from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Scheme, SchemeSlab


class SchemeSlabInline(admin.TabularInline):
    model = SchemeSlab
    extra = 1


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "scheme_code",
        "scheme_type",
        "start_date",
        "end_date",
        "is_active"
    )

    list_filter = (
        "scheme_type",
        "is_active",
        "is_combinable"
    )

    search_fields = (
        "name",
        "scheme_code",
        "description"
    )

    filter_horizontal = ("applicable_variants",)

    inlines = [SchemeSlabInline]


@admin.register(SchemeSlab)
class SchemeSlabAdmin(admin.ModelAdmin):

    list_display = (
        "scheme",
        "min_quantity",
        "max_quantity",
        "discount_percentage"
    )