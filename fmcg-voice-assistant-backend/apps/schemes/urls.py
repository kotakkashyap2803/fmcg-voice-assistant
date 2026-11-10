from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SchemeViewSet, SchemeCalculationView

router = DefaultRouter()
router.register("schemes", SchemeViewSet, basename="scheme")

urlpatterns = [
    path(
        "schemes/calculate/",
        SchemeCalculationView.as_view(),
        name="scheme-calculate"
    ),
    path("", include(router.urls)),
]