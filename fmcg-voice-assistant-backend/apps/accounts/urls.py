from django.urls import path

from .views import (
    HealthCheckView,
    LoginView,
    LogoutView,
    CurrentUserView,
    TokenRefreshView,
)


urlpatterns = [

    path(
        "health/",
        HealthCheckView.as_view(),
        name="health-check"
    ),

    path(
        "auth/login/",
        LoginView.as_view(),
        name="login"
    ),

    path(
        "auth/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"
    ),

    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="logout"
    ),

    path(
        "auth/me/",
        CurrentUserView.as_view(),
        name="current-user"
    ),

]