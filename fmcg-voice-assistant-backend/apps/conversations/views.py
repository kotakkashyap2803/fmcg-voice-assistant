from django.shortcuts import render

# Create your views here.
from django.db.models import Prefetch

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Conversation,
    ConversationMessage,
    ConversationCapture
)

from .serializers import (
    ConversationSerializer,
    ConversationMessageSerializer,
    ConversationCaptureSerializer,
    StartConversationSerializer,
    AddMessageSerializer,
    CompleteConversationSerializer
)

from .services import ConversationService


class ConversationViewSet(viewsets.ReadOnlyModelViewSet):

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Conversation.objects.select_related(
            "retailer",
            "handled_by"
        ).prefetch_related(
            "messages",
            "captures__variant__product"
        )

        retailer_id = self.request.query_params.get("retailer_id")
        conversation_status = self.request.query_params.get("status")
        outcome = self.request.query_params.get("outcome")

        if retailer_id:
            queryset = queryset.filter(retailer_id=retailer_id)

        if conversation_status:
            queryset = queryset.filter(status=conversation_status)

        if outcome:
            queryset = queryset.filter(outcome=outcome)

        return queryset

    def get_serializer_class(self):
        return ConversationSerializer

    @action(detail=False, methods=["post"])
    def start(self, request):

        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = ConversationService.start_conversation(
            retailer=serializer.validated_data["retailer_id"],
            user=request.user,
            channel=serializer.validated_data["channel"],
            language=serializer.validated_data["language"]
        )

        return Response(
            {
                "success": True,
                "message": "Conversation started successfully.",
                "data": ConversationSerializer(conversation).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):

        conversation = self.get_object()

        if request.method == "GET":
            messages = conversation.messages.all()

            return Response({
                "success": True,
                "data": ConversationMessageSerializer(
                    messages,
                    many=True
                ).data
            })

        serializer = AddMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = ConversationService.add_message(
                conversation.id,
                serializer.validated_data
            )

            return Response(
                {
                    "success": True,
                    "data": ConversationMessageSerializer(message).data
                },
                status=status.HTTP_201_CREATED
            )

        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get", "post"])
    def captures(self, request, pk=None):

        conversation = self.get_object()

        if request.method == "GET":
            captures = conversation.captures.select_related(
                "variant",
                "variant__product"
            )

            return Response({
                "success": True,
                "data": ConversationCaptureSerializer(
                    captures,
                    many=True
                ).data
            })

        serializer = ConversationCaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            capture = ConversationService.add_capture(
                conversation.id,
                serializer.validated_data
            )

            return Response(
                {
                    "success": True,
                    "data": ConversationCaptureSerializer(capture).data
                },
                status=status.HTTP_201_CREATED
            )

        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )


    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):

        conversation = self.get_object()

        try:
            conversation = ConversationService.complete_conversation(
                conversation_id=conversation.id
            )

            return Response({
                "success": True,
                "message": "Conversation completed successfully.",
                "data": ConversationSerializer(conversation).data
            })

        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )



class ConversationHistoryView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, retailer_id):

        conversations = Conversation.objects.filter(
            retailer_id=retailer_id
        ).select_related(
            "retailer",
            "handled_by"
        ).prefetch_related(
            "messages",
            "captures__variant__product"
        )

        serializer = ConversationSerializer(
            conversations,
            many=True
        )

        return Response({
            "success": True,
            "count": conversations.count(),
            "data": serializer.data
        })