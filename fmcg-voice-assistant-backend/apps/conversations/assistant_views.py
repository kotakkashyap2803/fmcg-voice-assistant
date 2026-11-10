
from django.shortcuts import get_object_or_404

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversations.models import Conversation
from services.business.assistant_service import AssistantService


class AssistantMessageSerializer(serializers.Serializer):

    conversation_id = serializers.IntegerField(min_value=1)

    message = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True
    )


class AssistantMessageView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = AssistantMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = serializer.validated_data["conversation_id"]
        message = serializer.validated_data["message"]

        conversation = get_object_or_404(
            Conversation,
            id=conversation_id
        )

        try:

            result = AssistantService.process_message(
                conversation_id=conversation.id,
                message=message,
                user=request.user
            )

            return Response(
                result,
                status=status.HTTP_200_OK
            )

        except ValueError as exc:

            return Response(
                {
                    "success": False,
                    "message": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
