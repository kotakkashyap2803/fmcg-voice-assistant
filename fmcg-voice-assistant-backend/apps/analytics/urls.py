from django.urls import path

from apps.analytics.views import DashboardAnalyticsView


urlpatterns = [
    path(
        "analytics/dashboard/",
        DashboardAnalyticsView.as_view(),
        name="analytics-dashboard"
    ),
]