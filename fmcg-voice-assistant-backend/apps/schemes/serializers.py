from rest_framework import serializers
from django.utils import timezone

from .models import Scheme, SchemeSlab
from apps.catalogue.models import ProductVariant


class SchemeSlabSerializer(serializers.ModelSerializer):

    class Meta:
        model = SchemeSlab
        fields = [
            "id",
            "min_quantity",
            "max_quantity",
            "discount_percentage"
        ]


class SchemeSerializer(serializers.ModelSerializer):

    slabs = SchemeSlabSerializer(many=True, required=False)
    applicable_variant_ids = serializers.PrimaryKeyRelatedField(
        source="applicable_variants",
        many=True,
        queryset=ProductVariant.objects.all(),
        required=False
    )

    class Meta:
        model = Scheme
        fields = [
            "id",
            "name",
            "scheme_code",
            "description",
            "scheme_type",
            "applicable_variant_ids",
            "buy_quantity",
            "free_quantity",
            "discount_percentage",
            "min_quantity",
            "start_date",
            "end_date",
            "is_active",
            "is_combinable",
            "max_discount_amount",
            "slabs",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None)
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None)
        )

        scheme_type = attrs.get(
            "scheme_type",
            getattr(self.instance, "scheme_type", None)
        )

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                "End date must be later than start date."
            )

        if scheme_type == Scheme.SchemeType.BUY_X_GET_Y:
            buy = attrs.get(
                "buy_quantity",
                getattr(self.instance, "buy_quantity", None)
            )
            free = attrs.get(
                "free_quantity",
                getattr(self.instance, "free_quantity", None)
            )

            if not buy or not free:
                raise serializers.ValidationError(
                    "Buy X Get Y requires buy_quantity and free_quantity."
                )

        if scheme_type == Scheme.SchemeType.PERCENTAGE:
            percentage = attrs.get(
                "discount_percentage",
                getattr(self.instance, "discount_percentage", None)
            )
            if percentage is None or percentage <= 0:
                raise serializers.ValidationError(
                    "Percentage discount must be greater than zero."
                )

        return attrs

    def create(self, validated_data):
        slabs_data = validated_data.pop("slabs", [])
        variants = validated_data.pop("applicable_variants", [])

        scheme = Scheme.objects.create(**validated_data)
        scheme.applicable_variants.set(variants)

        for slab in slabs_data:
            SchemeSlab.objects.create(scheme=scheme, **slab)

        return scheme

    def update(self, instance, validated_data):
        slabs_data = validated_data.pop("slabs", None)
        variants = validated_data.pop("applicable_variants", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if variants is not None:
            instance.applicable_variants.set(variants)

        if slabs_data is not None:
            instance.slabs.all().delete()

            for slab in slabs_data:
                SchemeSlab.objects.create(
                    scheme=instance,
                    **slab
                )

        return instance


class SchemeCalculationSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)