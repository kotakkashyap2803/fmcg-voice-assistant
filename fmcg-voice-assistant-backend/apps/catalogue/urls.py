from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    BrandViewSet,
    ProductViewSet,
    InventoryViewSet,
    InventoryAdjustmentView,
    InventoryTransactionViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("products", ProductViewSet, basename="product")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register(
    "inventory-transactions",
    InventoryTransactionViewSet,
    basename="inventory-transaction"
)

urlpatterns = [

    path("inventory/adjust/", InventoryAdjustmentView.as_view(),
        name="inventory-adjust"),

    path("", include(router.urls)),
]