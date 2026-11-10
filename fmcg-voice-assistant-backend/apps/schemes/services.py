from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Prefetch
from django.utils import timezone

from .models import Scheme
from apps.catalogue.models import ProductVariant

from django.db import models


class SchemeService:

    @staticmethod
    def money(value):
        return Decimal(value).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    @staticmethod
    def get_active_schemes(variant_id):
        now = timezone.now()

        return (
            Scheme.objects.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now,
                applicable_variants__id=variant_id
            )
            .prefetch_related("slabs")
            .distinct()
        )

    @staticmethod
    def calculate_scheme(scheme, variant, quantity):

        unit_price = Decimal(variant.selling_price)
        subtotal = SchemeService.money(unit_price * quantity)

        discount = Decimal("0.00")
        free_quantity = 0
        message = ""

        if quantity < scheme.min_quantity:
            return None

        if scheme.scheme_type == Scheme.SchemeType.BUY_X_GET_Y:

            buy = scheme.buy_quantity
            free = scheme.free_quantity

            if not buy or not free:
                return None

            free_quantity = (quantity // buy) * free

            message = (
                f"Buy {buy}, get {free} free. "
                f"You receive {free_quantity} free units."
            )

        elif scheme.scheme_type == Scheme.SchemeType.PERCENTAGE:

            percentage = Decimal(scheme.discount_percentage)

            discount = SchemeService.money(
                subtotal * percentage / Decimal("100")
            )

            message = f"{percentage}% discount applied."

        elif scheme.scheme_type == Scheme.SchemeType.QUANTITY_SLAB:

            eligible_slab = (
                scheme.slabs.filter(
                    min_quantity__lte=quantity
                )
                .filter(
                    models.Q(max_quantity__isnull=True) |
                    models.Q(max_quantity__gte=quantity)
                )
                .order_by("-min_quantity")
                .first()
            )

            if not eligible_slab:
                return None

            percentage = Decimal(
                eligible_slab.discount_percentage
            )

            discount = SchemeService.money(
                subtotal * percentage / Decimal("100")
            )

            message = (
                f"{percentage}% discount for ordering "
                f"{quantity} units."
            )

        elif scheme.scheme_type == Scheme.SchemeType.COMBO:
            # Combo calculation requires multiple cart items.
            return None

        if scheme.max_discount_amount is not None:
            discount = min(
                discount,
                Decimal(scheme.max_discount_amount)
            )

        discount = min(discount, subtotal)

        final_amount = SchemeService.money(subtotal - discount)

        return {
            "scheme_id": scheme.id,
            "scheme_name": scheme.name,
            "scheme_code": scheme.scheme_code,
            "scheme_type": scheme.scheme_type,
            "quantity": quantity,
            "free_quantity": free_quantity,
            "unit_price": str(SchemeService.money(unit_price)),
            "subtotal": str(subtotal),
            "discount_amount": str(SchemeService.money(discount)),
            "final_amount": str(final_amount),
            "message": message,
            "is_combinable": scheme.is_combinable
        }

    @staticmethod
    def calculate_offers(variant_id, quantity):

        try:
            variant = ProductVariant.objects.select_related(
                "product"
            ).get(
                id=variant_id,
                is_active=True,
                product__is_active=True
            )
        except ProductVariant.DoesNotExist:
            raise ValueError("Product variant not found or inactive.")

        schemes = SchemeService.get_active_schemes(variant_id)

        offers = []

        for scheme in schemes:
            result = SchemeService.calculate_scheme(
                scheme,
                variant,
                quantity
            )

            if result:
                offers.append(result)

        offers.sort(
            key=lambda item: (
                Decimal(item["subtotal"]) -
                Decimal(item["final_amount"])
            ),
            reverse=True
        )

        return {
            "product": variant.product.name,
            "variant": variant.variant_name,
            "sku": variant.sku,
            "quantity": quantity,
            "offers": offers,
            "best_offer": offers[0] if offers else None
        }