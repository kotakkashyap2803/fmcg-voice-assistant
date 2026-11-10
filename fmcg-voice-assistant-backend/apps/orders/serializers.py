from decimal import Decimal

from rest_framework import serializers

from apps.orders.models import (
    Order,
    OrderItem,
    OrderItemScheme,
    OrderStatusHistory,
)


class OrderItemSchemeSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItemScheme
        fields = [
            "id",
            "scheme",
            "scheme_name",
            "scheme_code",
            "scheme_type",
            "discount_amount",
            "free_quantity",
            "created_at",
        ]

        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):

    applied_schemes = OrderItemSchemeSerializer(
        many=True,
        read_only=True
    )

    total_units = serializers.DecimalField(
        max_digits=13,
        decimal_places=3,
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "variant",
            "product_name",
            "variant_name",
            "sku",
            "quantity",
            "free_quantity",
            "total_units",
            "unit_price",
            "mrp",
            "subtotal",
            "discount_amount",
            "total_amount",
            "applied_schemes",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "product_name",
            "variant_name",
            "sku",
            "free_quantity",
            "unit_price",
            "mrp",
            "subtotal",
            "discount_amount",
            "total_amount",
            "applied_schemes",
            "created_at",
        ]


class OrderStatusHistorySerializer(serializers.ModelSerializer):

    changed_by_username = serializers.CharField(
        source="changed_by.username",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = OrderStatusHistory
        fields = [
            "id",
            "previous_status",
            "new_status",
            "remarks",
            "changed_by",
            "changed_by_username",
            "created_at",
        ]

        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):

    retailer_name = serializers.CharField(
        source="retailer.name",
        read_only=True
    )

    retailer_code = serializers.CharField(
        source="retailer.retailer_code",
        read_only=True
    )

    conversation_id = serializers.IntegerField(
        source="conversation.id",
        read_only=True,
        allow_null=True
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True
    )

    confirmed_by_username = serializers.CharField(
        source="confirmed_by.username",
        read_only=True,
        allow_null=True
    )

    items = OrderItemSerializer(many=True, read_only=True)

    status_history = OrderStatusHistorySerializer(
        many=True,
        read_only=True
    )

    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "retailer",
            "retailer_name",
            "retailer_code",
            "conversation",
            "conversation_id",
            "created_by",
            "created_by_username",
            "confirmed_by",
            "confirmed_by_username",
            "status",
            "subtotal",
            "discount_amount",
            "total_amount",
            "notes",
            "items",
            "item_count",
            "status_history",
            "created_at",
            "updated_at",
            "confirmed_at",
            "cancelled_at",
        ]

        read_only_fields = fields

    def get_item_count(self, obj):
        return obj.items.count()


class CreateOrderDraftSerializer(serializers.Serializer):

    retailer_id = serializers.IntegerField(min_value=1)

    conversation_id = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )


class AddOrderItemSerializer(serializers.Serializer):

    variant_id = serializers.IntegerField(min_value=1)

    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001")
    )


class CancelOrderSerializer(serializers.Serializer):

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default=""
    )