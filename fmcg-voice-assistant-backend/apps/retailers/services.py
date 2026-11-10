from django.db.models import Q

from rest_framework.exceptions import (
    NotFound,
    ValidationError
)

from .models import Retailer, RetailerContact


class RetailerService:

    @staticmethod
    def get_queryset():

        return Retailer.objects.select_related(
            "sales_representative"
        ).prefetch_related("contacts")

    @staticmethod
    def get_retailer(retailer_id):

        try:
            return RetailerService.get_queryset().get(
                id=retailer_id
            )

        except Retailer.DoesNotExist:
            raise NotFound("Retailer not found.")

    @staticmethod
    def search_retailers(query):

        queryset = RetailerService.get_queryset()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(shop_name__icontains=query)
                | Q(retailer_code__icontains=query)
                | Q(primary_phone__icontains=query)
                | Q(territory__icontains=query)
            )

        return queryset

    @staticmethod
    def identify_caller(phone):

        normalized_phone = phone.strip()

        retailers = RetailerService.get_queryset().filter(
            Q(primary_phone=normalized_phone)
            | Q(contacts__phone=normalized_phone)
        ).distinct()

        if not retailers.exists():
            return {
                "identified": False,
                "message": "No retailer found for this phone number.",
                "retailers": []
            }

        matches = list(retailers)

        if len(matches) > 1:
            return {
                "identified": False,
                "multiple_matches": True,
                "message": "Multiple retailers found. Please select one.",
                "retailers": matches
            }

        retailer = matches[0]

        if retailer.business_status != Retailer.BusinessStatus.ACTIVE:
            return {
                "identified": True,
                "authorized": False,
                "message": "This retailer account is not active.",
                "retailer": retailer
            }

        return {
            "identified": True,
            "authorized": True,
            "message": "Retailer identified successfully.",
            "retailer": retailer
        }

    @staticmethod
    def get_retailer_contacts(retailer_id):

        retailer = RetailerService.get_retailer(retailer_id)

        return retailer.contacts.all()