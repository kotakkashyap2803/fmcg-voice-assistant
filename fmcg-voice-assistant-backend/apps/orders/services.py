from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.orders.models import (
    Order,
    OrderItem,
    OrderItemScheme,
    OrderStatusHistory,
)
from apps.retailers.models import Retailer
from apps.catalogue.models import ProductVariant, Inventory
from apps.catalogue.services import InventoryService
from apps.schemes.services import SchemeService


class OrderService:

    @staticmethod
    def money(value):
        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    @staticmethod
    def quantity(value):
        return Decimal(str(value)).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP
        )

    @staticmethod
    @transaction.atomic
    def create_draft(retailer_id, user, conversation_id=None, notes=""):
        """
        Create an order draft for an active retailer.
        No inventory is deducted at this stage.
        """

        retailer = Retailer.objects.select_for_update().filter(
            id=retailer_id,
            business_status="ACTIVE"
        ).first()

        if not retailer:
            raise ValidationError("Active retailer not found.")

        conversation = None

        if conversation_id:
            from apps.conversations.models import Conversation

            conversation = Conversation.objects.filter(
                id=conversation_id,
                retailer=retailer
            ).first()

            if not conversation:
                raise ValidationError(
                    "Conversation does not exist for this retailer."
                )

        order = Order.objects.create(
            retailer=retailer,
            conversation=conversation,
            created_by=user,
            notes=notes
        )

        OrderStatusHistory.objects.create(
            order=order,
            previous_status="",
            new_status=Order.Status.DRAFT,
            remarks="Order draft created.",
            changed_by=user
        )

        return order

    @staticmethod
    @transaction.atomic
    def add_item(order_id, variant_id, quantity, user=None):
        """
        Add or update a product variant in a draft order.
        """

        order = Order.objects.select_for_update().filter(
            id=order_id
        ).first()

        if not order:
            raise ValidationError("Order not found.")

        if order.status != Order.Status.DRAFT:
            raise ValidationError(
                "Items can only be added to draft orders."
            )

        quantity = OrderService.quantity(quantity)

        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        variant = ProductVariant.objects.select_related(
            "product"
        ).filter(
            id=variant_id,
            is_active=True,
            product__is_active=True
        ).first()

        if not variant:
            raise ValidationError("Active product variant not found.")

        item = OrderItem.objects.filter(
            order=order,
            variant=variant
        ).first()

        if item:
            item.quantity += quantity
            item.free_quantity = Decimal("0")
            item.save(update_fields=["quantity", "free_quantity"])
        else:
            item = OrderItem.objects.create(
                order=order,
                variant=variant,
                product_name=variant.product.name,
                variant_name=variant.variant_name,
                sku=variant.sku,
                quantity=quantity,
                free_quantity=Decimal("0"),
                unit_price=OrderService.money(variant.selling_price),
                mrp=OrderService.money(variant.mrp),
                subtotal=Decimal("0.00"),
                discount_amount=Decimal("0.00"),
                total_amount=Decimal("0.00")
            )

        OrderService.calculate_order(order.id)

        return item

    @staticmethod
    @transaction.atomic
    def calculate_order(order_id):
        """
        Recalculate order totals and apply the best eligible scheme
        for each item. Scheme calculations remain owned by SchemeService.
        """

        order = Order.objects.select_for_update().filter(
            id=order_id
        ).first()

        if not order:
            raise ValidationError("Order not found.")

        if order.status != Order.Status.DRAFT:
            raise ValidationError(
                "Only draft orders can be recalculated."
            )

        items = order.items.select_related(
            "variant",
            "variant__product"
        ).all()

        if not items.exists():
            raise ValidationError("Add at least one item to the order.")

        order_subtotal = Decimal("0.00")
        order_discount = Decimal("0.00")
        order_total = Decimal("0.00")

        for item in items:

            variant = item.variant

            if not variant.is_active or not variant.product.is_active:
                raise ValidationError(
                    f"Product variant {variant.sku} is no longer active."
                )

            unit_price = OrderService.money(variant.selling_price)
            mrp = OrderService.money(variant.mrp)
            quantity = OrderService.quantity(item.quantity)

            if quantity <= 0:
                raise ValidationError(
                    f"Invalid quantity for {variant.sku}."
                )

            subtotal = OrderService.money(unit_price * quantity)

            # Reset scheme results before recalculation.
            item.applied_schemes.all().delete()

            best_scheme_result = None
            best_scheme = None

            active_schemes = SchemeService.get_active_schemes(
                variant.id
            )

            # Select the scheme providing the highest monetary discount.
            # We do not stack multiple schemes in this implementation.
            for scheme in active_schemes:

                result = SchemeService.calculate_scheme(
                    scheme,
                    variant,
                    quantity
                )

                if result is None:
                    continue

                discount = OrderService.money(
                    result.get("discount_amount", 0)
                )

                if (
                    best_scheme_result is None
                    or discount > OrderService.money(
                        best_scheme_result.get("discount_amount", 0)
                    )
                ):
                    best_scheme_result = result
                    best_scheme = scheme

            free_quantity = Decimal("0")
            discount_amount = Decimal("0.00")
            final_amount = subtotal

            if best_scheme_result:
                free_quantity = OrderService.quantity(
                    best_scheme_result.get("free_quantity", 0)
                )

                discount_amount = OrderService.money(
                    best_scheme_result.get("discount_amount", 0)
                )

                final_amount = OrderService.money(
                    best_scheme_result.get("final_amount", subtotal)
                )

                if discount_amount < 0 or discount_amount > subtotal:
                    raise ValidationError(
                        f"Invalid scheme discount for {variant.sku}."
                    )

                if free_quantity < 0:
                    raise ValidationError(
                        f"Invalid free quantity for {variant.sku}."
                    )

                OrderItemScheme.objects.create(
                    order_item=item,
                    scheme=best_scheme,
                    scheme_name=best_scheme.name,
                    scheme_code=best_scheme.scheme_code,
                    scheme_type=best_scheme.scheme_type,
                    discount_amount=discount_amount,
                    free_quantity=free_quantity
                )

            item.product_name = variant.product.name
            item.variant_name = variant.variant_name
            item.sku = variant.sku
            item.unit_price = unit_price
            item.mrp = mrp
            item.subtotal = subtotal
            item.free_quantity = free_quantity
            item.discount_amount = discount_amount
            item.total_amount = final_amount

            item.save()

            order_subtotal += subtotal
            order_discount += discount_amount
            order_total += final_amount

        order.subtotal = OrderService.money(order_subtotal)
        order.discount_amount = OrderService.money(order_discount)
        order.total_amount = OrderService.money(order_total)

        order.save(
            update_fields=[
                "subtotal",
                "discount_amount",
                "total_amount",
                "updated_at"
            ]
        )

        return order

    @staticmethod
    @transaction.atomic
    def confirm_order(order_id, user):
        """
        Confirm an order and deduct purchased + free units from inventory.

        The transaction and row locks prevent concurrent orders from
        overselling available stock.
        """

        order = Order.objects.select_for_update().filter(
            id=order_id
        ).first()

        if not order:
            raise ValidationError("Order not found.")

        # Idempotency: never deduct stock twice.
        if order.status == Order.Status.CONFIRMED:
            return order

        if order.status != Order.Status.DRAFT:
            raise ValidationError(
                "Only draft orders can be confirmed."
            )

        # Refresh prices and schemes before final stock validation.
        OrderService.calculate_order(order_id)

        order.refresh_from_db()

        items = list(
            order.items.select_related("variant").order_by("variant_id")
        )

        if not items:
            raise ValidationError("Cannot confirm an empty order.")

        # Lock inventory rows in a consistent order.
        inventory_rows = list(
            Inventory.objects.select_for_update()
            .filter(
                variant_id__in=[item.variant_id for item in items]
            )
            .order_by("variant_id")
        )

        inventory_by_variant = {
            inventory.variant_id: inventory
            for inventory in inventory_rows
        }

        # Validate all inventory before changing any stock.
        for item in items:

            inventory = inventory_by_variant.get(item.variant_id)

            if not inventory:
                raise ValidationError(
                    f"Inventory record missing for SKU {item.sku}."
                )

            required_quantity = (
                item.quantity + item.free_quantity
            )

            if inventory.quantity_on_hand < required_quantity:
                raise ValidationError(
                    f"Insufficient stock for {item.sku}. "
                    f"Available: {inventory.quantity_on_hand}, "
                    f"Required: {required_quantity}."
                )

        # Deduct stock using the existing InventoryService.
        for item in items:

            required_quantity = (
                item.quantity + item.free_quantity
            )

            InventoryService.adjust_stock(
                variant_id=item.variant_id,
                transaction_type="OUT",
                quantity=required_quantity,
                reason="Order confirmation",
                user=user,
                reference=order.order_number
            )

        previous_status = order.status

        order.status = Order.Status.CONFIRMED
        order.confirmed_by = user
        order.confirmed_at = timezone.now()

        order.save(
            update_fields=[
                "status",
                "confirmed_by",
                "confirmed_at",
                "updated_at"
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=Order.Status.CONFIRMED,
            remarks="Order confirmed and inventory deducted.",
            changed_by=user
        )

        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order_id, user, reason=""):
        """
        Cancel an order.
        Confirmed orders restore their stock exactly once.
        """

        order = Order.objects.select_for_update().filter(
            id=order_id
        ).first()

        if not order:
            raise ValidationError("Order not found.")

        if order.status == Order.Status.CANCELLED:
            return order

        if order.status == Order.Status.DRAFT:
            previous_status = order.status

        elif order.status == Order.Status.CONFIRMED:

            items = list(
                order.items.select_related("variant").order_by(
                    "variant_id"
                )
            )

            # Restore purchased and free units.
            for item in items:

                restored_quantity = (
                    item.quantity + item.free_quantity
                )

                InventoryService.adjust_stock(
                    variant_id=item.variant_id,
                    transaction_type="IN",
                    quantity=restored_quantity,
                    reason="Order cancellation - stock restoration",
                    user=user,
                    reference=order.order_number
                )

            previous_status = order.status

        else:
            raise ValidationError("This order cannot be cancelled.")

        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()

        order.save(
            update_fields=[
                "status",
                "cancelled_at",
                "updated_at"
            ]
        )

        OrderStatusHistory.objects.create(
            order=order,
            previous_status=previous_status,
            new_status=Order.Status.CANCELLED,
            remarks=reason or "Order cancelled.",
            changed_by=user
        )

        return order