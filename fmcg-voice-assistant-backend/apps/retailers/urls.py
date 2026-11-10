from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RetailerViewSet,
    CallerIdentificationView,
)

router = DefaultRouter()

router.register(
    r"retailers",
    RetailerViewSet,
    basename="retailer"
)

urlpatterns = [

    path(
        "retailers/identify-caller/",
        CallerIdentificationView.as_view(),
        name="identify-caller"
    ),

    path(
        "",
        include(router.urls)
    ),

]