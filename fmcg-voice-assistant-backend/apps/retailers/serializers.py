from django.db import transaction
from rest_framework import serializers

from .models import Retailer, RetailerContact


class RetailerContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = RetailerContact
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "contact_type",
            "is_primary",
        ]
        read_only_fields = ["id"]


class RetailerSerializer(serializers.ModelSerializer):

    contacts = RetailerContactSerializer(
        many=True,
        required=False
    )

    sales_representative_name = serializers.SerializerMethodField()

    class Meta:
        model = Retailer
        fields = [
            "id",
            "retailer_code",
            "name",
            "shop_name",
            "retailer_type",
            "primary_phone",
            "email",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "pincode",
            "territory",
            "sales_representative",
            "sales_representative_name",
            "business_status",
            "notes",
            "contacts",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "sales_representative_name",
        ]

    def get_sales_representative_name(self, obj):

        if obj.sales_representative:
            return obj.sales_representative.get_full_name() or (
                obj.sales_representative.username
            )

        return None

    def validate_primary_phone(self, value):
        return value.strip()

    def validate(self, attrs):

        contacts = attrs.get("contacts", [])

        primary_contacts = [
            contact for contact in contacts
            if contact.get("is_primary", False)
        ]

        if len(primary_contacts) > 1:
            raise serializers.ValidationError({
                "contacts": "Only one contact can be marked as primary."
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):

        contacts_data = validated_data.pop("contacts", [])

        retailer = Retailer.objects.create(**validated_data)

        for contact_data in contacts_data:
            RetailerContact.objects.create(
                retailer=retailer,
                **contact_data
            )

        return retailer

    @transaction.atomic
    def update(self, instance, validated_data):

        contacts_data = validated_data.pop("contacts", None)

        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()

        if contacts_data is not None:

            # Replace the existing contact collection atomically.
            instance.contacts.all().delete()

            for contact_data in contacts_data:
                RetailerContact.objects.create(
                    retailer=instance,
                    **contact_data
                )

        return instance


class RetailerListSerializer(serializers.ModelSerializer):

    sales_representative_name = serializers.SerializerMethodField()

    class Meta:
        model = Retailer
        fields = [
            "id",
            "retailer_code",
            "name",
            "shop_name",
            "retailer_type",
            "primary_phone",
            "city",
            "territory",
            "sales_representative_name",
            "business_status",
        ]

    def get_sales_representative_name(self, obj):

        if obj.sales_representative:
            return (
                obj.sales_representative.get_full_name()
                or obj.sales_representative.username
            )

        return None