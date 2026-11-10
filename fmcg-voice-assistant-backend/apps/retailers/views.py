from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError

from .models import Retailer
from .serializers import (
    RetailerSerializer,
    RetailerListSerializer,
    RetailerContactSerializer,
)
from .services import RetailerService


class RetailerPagination(PageNumberPagination):

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class RetailerViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    pagination_class = RetailerPagination

    def get_queryset(self):

        queryset = RetailerService.get_queryset()

        # Search
        search = self.request.query_params.get("search")

        if search:
            queryset = RetailerService.search_retailers(search)

        # Filter by territory
        territory = self.request.query_params.get("territory")

        if territory:
            queryset = queryset.filter(
                territory__iexact=territory
            )

        # Filter by retailer type
        retailer_type = self.request.query_params.get("retailer_type")

        if retailer_type:
            queryset = queryset.filter(
                retailer_type=retailer_type.upper()
            )

        # Filter by business status
        business_status = self.request.query_params.get(
            "business_status"
        )

        if business_status:
            queryset = queryset.filter(
                business_status=business_status.upper()
            )

        # Filter by sales representative
        sales_rep = self.request.query_params.get(
            "sales_representative"
        )

        if sales_rep:
            if not sales_rep.isdigit():
                raise ValidationError({
                    "sales_representative": "Must be a valid user ID."
                })

            queryset = queryset.filter(
                sales_representative_id=int(sales_rep)
            )

        # Ordering
        ordering = self.request.query_params.get(
            "ordering",
            "name"
        )

        allowed_ordering = {
            "name",
            "-name",
            "shop_name",
            "-shop_name",
            "created_at",
            "-created_at",
        }

        if ordering not in allowed_ordering:
            raise ValidationError({
                "ordering": "Unsupported ordering field."
            })

        return queryset.order_by(ordering)

    def get_serializer_class(self):

        if self.action == "list":
            return RetailerListSerializer

        return RetailerSerializer

    def list(self, request, *args, **kwargs):

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response({
                "success": True,
                "message": "Retailers retrieved successfully.",
                "data": serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "success": True,
            "message": "Retailers retrieved successfully.",
            "data": serializer.data
        })

    def retrieve(self, request, *args, **kwargs):

        instance = self.get_object()

        serializer = self.get_serializer(instance)

        return Response({
            "success": True,
            "message": "Retailer details retrieved successfully.",
            "data": serializer.data
        })

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({
            "success": True,
            "message": "Retailer created successfully.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({
            "success": True,
            "message": "Retailer updated successfully.",
            "data": serializer.data
        })

    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()

        instance.business_status = Retailer.BusinessStatus.INACTIVE

        instance.save(update_fields=[
            "business_status",
            "updated_at"
        ])

        return Response({
            "success": True,
            "message": "Retailer deactivated successfully."
        })

    @action(
        detail=True,
        methods=["get"],
        url_path="contacts"
    )
    def contacts(self, request, pk=None):

        retailer = self.get_object()

        serializer = RetailerContactSerializer(
            retailer.contacts.all(),
            many=True
        )

        return Response({
            "success": True,
            "data": serializer.data
        })

    @action(
        detail=True,
        methods=["get"],
        url_path="history"
    )
    def history(self, request, pk=None):

        retailer = self.get_object()

        # Conversation history will be connected
        # when the Conversations module is implemented.

        return Response({
            "success": True,
            "message": "Conversation history will be available after the Conversations module is implemented.",
            "data": {
                "retailer_id": retailer.id,
                "conversations": []
            }
        })


class CallerIdentificationView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        phone = request.data.get("phone")

        if not phone:
            raise ValidationError({
                "phone": "Phone number is required."
            })

        if not isinstance(phone, str):
            raise ValidationError({
                "phone": "Phone number must be a string."
            })

        result = RetailerService.identify_caller(phone)

        if result.get("retailer"):

            from .serializers import RetailerSerializer

            result["retailer"] = RetailerSerializer(
                result["retailer"]
            ).data

        if result.get("retailers"):

            from .serializers import RetailerListSerializer

            result["retailers"] = RetailerListSerializer(
                result["retailers"],
                many=True
            ).data

        return Response({
            "success": True,
            "data": result
        })