import re
from decimal import Decimal, InvalidOperation

from django.db.models import Q

from apps.catalogue.models import (
    Product,
    ProductVariant,
)


class ProductResolver:

    UNIT_ALIASES = {
        "G": "G",
        "GRAM": "G",
        "GRAMS": "G",

        "KG": "KG",
        "KGS": "KG",
        "KILOGRAM": "KG",
        "KILOGRAMS": "KG",

        "ML": "ML",
        "MILLILITRE": "ML",
        "MILLILITRES": "ML",
        "MILLILITER": "ML",
        "MILLILITERS": "ML",

        "L": "L",
        "LT": "L",
        "LTR": "L",
        "LITRE": "L",
        "LITRES": "L",
        "LITER": "L",
        "LITERS": "L",

        "PCS": "PCS",
        "PC": "PCS",
        "PIECE": "PCS",
        "PIECES": "PCS",

        "PACK": "PACK",
        "PACKS": "PACK",

        "BOX": "BOX",
        "BOXES": "BOX",
    }

    @staticmethod
    def _get_value(mention, field, default=None):
        """
        Supports both Pydantic objects and dictionaries.
        """
        if isinstance(mention, dict):
            return mention.get(field, default)

        return getattr(mention, field, default)

    @classmethod
    def _parse_pack_size(cls, pack_size):
        """
        Examples:
            500 ml     -> (Decimal("500"), "ML")
            1 litre    -> (Decimal("1"), "L")
            200 g      -> (Decimal("200"), "G")
            1.5 kg     -> (Decimal("1.5"), "KG")

        Returns None if the pack size cannot be interpreted.
        """

        if not pack_size:
            return None

        value = str(pack_size).strip().upper()

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*([A-Z]+)?",
            value
        )

        if not match:
            return None

        try:
            size = Decimal(match.group(1))
        except InvalidOperation:
            return None

        raw_unit = match.group(2)

        if not raw_unit:
            return size, None

        normalized_unit = cls.UNIT_ALIASES.get(raw_unit)

        if not normalized_unit:
            return None

        return size, normalized_unit

    @staticmethod
    def _matches_pack_size(variant, requested_pack_size):
        parsed = ProductResolver._parse_pack_size(requested_pack_size)

        if not parsed:
            return False

        requested_size, requested_unit = parsed

        requested_unit = str(requested_unit).upper().strip()
        stored_unit = str(variant.unit).upper().strip()

        stored_size = Decimal(str(variant.pack_size))

        # Convert everything to base units.
        conversion = {
            "G": ("MASS", Decimal("1")),
            "GRAM": ("MASS", Decimal("1")),
            "GRAMS": ("MASS", Decimal("1")),
            "KG": ("MASS", Decimal("1000")),

            "ML": ("VOLUME", Decimal("1")),
            "L": ("VOLUME", Decimal("1000")),
            "LTR": ("VOLUME", Decimal("1000")),
            "LITRE": ("VOLUME", Decimal("1000")),
            "LITRES": ("VOLUME", Decimal("1000")),

            "PCS": ("COUNT", Decimal("1")),
            "PACK": ("PACK", Decimal("1")),
            "BOX": ("BOX", Decimal("1")),
        }

        requested_conversion = conversion.get(requested_unit)
        stored_conversion = conversion.get(stored_unit)

        if not requested_conversion or not stored_conversion:
            return False

        requested_group, requested_factor = requested_conversion
        stored_group, stored_factor = stored_conversion

        if requested_group != stored_group:
            return False

        requested_base = requested_size * requested_factor
        stored_base = stored_size * stored_factor

        return requested_base == stored_base

    @classmethod
    def resolve(cls, mention):
        """
        Resolves an AI-extracted product mention against the database.

        Possible statuses:
            RESOLVED
            PRODUCT_NOT_FOUND
            VARIANT_REQUIRED
            VARIANT_NOT_FOUND
            NO_ACTIVE_VARIANTS
        """

        product_name = cls._get_value(
            mention, "product_name", ""
        )

        brand_name = cls._get_value(
            mention, "brand_name"
        )

        requested_pack_size = cls._get_value(
            mention, "pack_size"
        )

        product_name = str(product_name or "").strip()
        brand_name = str(brand_name or "").strip()

        if not product_name and not brand_name:
            return {
                "status": "PRODUCT_NOT_FOUND",
                "message": "Please tell me the product name.",
                "product": None,
                "variant": None,
                "variants": [],
            }

        products = Product.objects.filter(
            is_active=True
        ).filter(
            Q(name__icontains=product_name)
            | Q(product_code__icontains=product_name)
            | Q(aliases__alias__icontains=product_name)
        ).select_related(
            "brand",
            "category"
        ).distinct()

        # Apply the brand filter when Gemini identified one.
        if brand_name:
            products = products.filter(
                brand__name__icontains=brand_name
            )

        # If the product name did not identify anything, try
        # interpreting the mention as a brand name.
        if not products.exists() and brand_name:
            products = Product.objects.filter(
                is_active=True,
                brand__name__icontains=brand_name
            ).select_related(
                "brand",
                "category"
            ).distinct()

        if not products.exists():
            return {
                "status": "PRODUCT_NOT_FOUND",
                "message": (
                    f"I could not find {product_name or brand_name} "
                    "in the product catalogue."
                ),
                "product": None,
                "variant": None,
                "variants": [],
            }

        variants = ProductVariant.objects.filter(
            product__in=products,
            product__is_active=True,
            is_active=True
        ).select_related(
            "product",
            "product__brand",
            "product__category"
        ).order_by(
            "pack_size"
        )

        variant_list = list(variants)

        if not variant_list:
            return {
                "status": "NO_ACTIVE_VARIANTS",
                "message": (
                    "This product currently has no active pack sizes."
                ),
                "product": products.first(),
                "variant": None,
                "variants": [],
            }

        # If the retailer specified a pack size, resolve that exact
        # variant rather than selecting an arbitrary one.
        if requested_pack_size:
            matching_variants = [
                variant
                for variant in variant_list
                if cls._matches_pack_size(
                    variant,
                    requested_pack_size
                )
            ]

            if not matching_variants:
                return {
                    "status": "VARIANT_NOT_FOUND",
                    "message": (
                        f"I could not find the "
                        f"{requested_pack_size} pack size. "
                        "Please choose an available pack size."
                    ),
                    "product": products.first(),
                    "variant": None,
                    "variants": variant_list,
                }

            if len(matching_variants) == 1:
                return {
                    "status": "RESOLVED",
                    "message": "Product and pack size resolved.",
                    "product": matching_variants[0].product,
                    "variant": matching_variants[0],
                    "variants": matching_variants,
                }

            return {
                "status": "VARIANT_REQUIRED",
                "message": "Please specify which pack size you need.",
                "product": matching_variants[0].product,
                "variant": None,
                "variants": matching_variants,
            }

        # Without a pack size, resolve only when there is exactly
        # one available variant.
        if len(variant_list) == 1:
            return {
                "status": "RESOLVED",
                "message": "Product resolved.",
                "product": variant_list[0].product,
                "variant": variant_list[0],
                "variants": variant_list,
            }

        return {
            "status": "VARIANT_REQUIRED",
            "message": (
                "This product is available in multiple pack sizes. "
                "Please specify the pack size."
            ),
            "product": variant_list[0].product,
            "variant": None,
            "variants": variant_list,
        }