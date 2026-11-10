
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet,
    ConversationHistoryView
)

from .assistant_views import AssistantMessageView


router = DefaultRouter()

router.register(
    "conversations",
    ConversationViewSet,
    basename="conversation"
)


urlpatterns = [

    # AI assistant endpoint
    path(
        "assistant/message/",
        AssistantMessageView.as_view(),
        name="assistant-message"
    ),

    # Retailer conversation history
    path(
        "retailers/<int:retailer_id>/conversation-history/",
        ConversationHistoryView.as_view(),
        name="retailer-conversation-history"
    ),

    # Standard conversation endpoints
    path("", include(router.urls)),
]
