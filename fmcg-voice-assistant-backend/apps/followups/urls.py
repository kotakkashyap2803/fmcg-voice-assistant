from rest_framework.routers import DefaultRouter

from apps.followups.views import FollowUpViewSet


router = DefaultRouter()

router.register(
    r"followups",
    FollowUpViewSet,
    basename="followup"
)

urlpatterns = router.urls