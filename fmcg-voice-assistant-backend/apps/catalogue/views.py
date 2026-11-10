from django.shortcuts import render

# Create your views here.
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Category,
    Brand,
    Product,
    Inventory,
    InventoryTransaction,
)
from .serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductSerializer,
    ProductVariantSerializer,
    InventorySerializer,
    InventoryAdjustmentSerializer,
    InventoryTransactionSerializer,
)
from .services import ProductService, InventoryService


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.select_related(
            "brand", "category"
        ).prefetch_related(
            "aliases", "variants", "variants__inventory"
        ).order_by("name")

    def get_serializer_class(self):
        if self.action == "variants":
            return ProductVariantSerializer
        return ProductSerializer

    @action(detail=False, methods=["get"])
    def search(self, request):
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response({
                "success": False,
                "message": "Provide a search query using ?q=",
                "data": []
            }, status=status.HTTP_400_BAD_REQUEST)

        products = ProductService.search_products(query)

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductSerializer(
                page, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)

        serializer = ProductSerializer(
            products, many=True, context=self.get_serializer_context()
        )

        return Response({
            "success": True,
            "message": "Products retrieved successfully.",
            "data": serializer.data
        })

    @action(detail=True, methods=["get"])
    def variants(self, request, pk=None):
        product = self.get_object()
        serializer = ProductVariantSerializer(
            product.variants.filter(is_active=True), many=True
        )
        return Response({
            "success": True,
            "data": serializer.data
        })

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        product = self.get_object()
        variants = product.variants.filter(is_active=True).select_related(
            "product"
        )

        inventory_rows = Inventory.objects.filter(
            variant__in=variants
        ).select_related("variant", "variant__product")

        serializer = InventorySerializer(inventory_rows, many=True)

        return Response({
            "success": True,
            "data": serializer.data
        })


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Inventory.objects.select_related(
        "variant", "variant__product"
    ).all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        inventory = self.get_queryset().filter(
            quantity_on_hand__lte=F("reorder_level")
        )

        serializer = self.get_serializer(inventory, many=True)

        return Response({
            "success": True,
            "count": inventory.count(),
            "data": serializer.data
        })


class InventoryAdjustmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InventoryAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        result = InventoryService.adjust_stock(
            variant_id=data["variant_id"],
            transaction_type=data["transaction_type"],
            quantity=data["quantity"],
            reason=data["reason"],
            user=request.user,
            reference=data.get("reference", "")
        )

        return Response({
            "success": True,
            "message": "Inventory updated successfully.",
            "data": {
                "inventory": InventorySerializer(
                    result["inventory"]
                ).data,
                "transaction": InventoryTransactionSerializer(
                    result["transaction"]
                ).data
            }
        }, status=status.HTTP_200_OK)


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryTransaction.objects.select_related(
        "variant", "variant__product", "created_by"
    ).all()
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]