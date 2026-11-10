from django.shortcuts import render

# Create your views here.
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.orders.models import Order
from apps.orders.serializers import (
    OrderSerializer,
    CreateOrderDraftSerializer,
    AddOrderItemSerializer,
    CancelOrderSerializer,
)
from apps.orders.services import OrderService


class OrderViewSet(ReadOnlyModelViewSet):

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):

        queryset = Order.objects.select_related(
            "retailer",
            "conversation",
            "created_by",
            "confirmed_by",
        ).prefetch_related(
            "items__applied_schemes",
            "status_history",
        )

        retailer_id = self.request.query_params.get("retailer_id")
        order_status = self.request.query_params.get("status")

        if retailer_id:
            queryset = queryset.filter(retailer_id=retailer_id)

        if order_status:
            queryset = queryset.filter(status=order_status.upper())

        return queryset

    @staticmethod
    def error_response(exc):
        if hasattr(exc, "messages"):
            message = " ".join(exc.messages)
        else:
            message = str(exc)

        return Response(
            {"success": False, "message": message},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, methods=["post"], url_path="draft")
    def create_draft(self, request):

        serializer = CreateOrderDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.create_draft(
                retailer_id=serializer.validated_data["retailer_id"],
                user=request.user,
                conversation_id=serializer.validated_data.get(
                    "conversation_id"
                ),
                notes=serializer.validated_data.get("notes", ""),
            )

            return Response(
                {
                    "success": True,
                    "message": "Order draft created successfully.",
                    "data": OrderSerializer(order).data,
                },
                status=status.HTTP_201_CREATED
            )

        except DjangoValidationError as exc:
            return self.error_response(exc)

    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request, pk=None):

        serializer = AddOrderItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = OrderService.add_item(
                order_id=pk,
                variant_id=serializer.validated_data["variant_id"],
                quantity=serializer.validated_data["quantity"],
                user=request.user,
            )

            order = Order.objects.get(id=item.order_id)

            return Response(
                {
                    "success": True,
                    "message": "Product added to order successfully.",
                    "data": OrderSerializer(order).data,
                },
                status=status.HTTP_200_OK
            )

        except DjangoValidationError as exc:
            return self.error_response(exc)

    @action(detail=True, methods=["post"], url_path="recalculate")
    def recalculate(self, request, pk=None):

        try:
            order = OrderService.calculate_order(pk)

            return Response(
                {
                    "success": True,
                    "message": "Order recalculated successfully.",
                    "data": OrderSerializer(order).data,
                }
            )

        except DjangoValidationError as exc:
            return self.error_response(exc)

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):

        try:
            order = OrderService.confirm_order(
                order_id=pk,
                user=request.user
            )

            return Response(
                {
                    "success": True,
                    "message": "Order confirmed successfully.",
                    "data": OrderSerializer(order).data,
                }
            )

        except DjangoValidationError as exc:
            return self.error_response(exc)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):

        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.cancel_order(
                order_id=pk,
                user=request.user,
                reason=serializer.validated_data.get("reason", "")
            )

            return Response(
                {
                    "success": True,
                    "message": "Order cancelled successfully.",
                    "data": OrderSerializer(order).data,
                }
            )

        except DjangoValidationError as exc:
            return self.error_response(exc)