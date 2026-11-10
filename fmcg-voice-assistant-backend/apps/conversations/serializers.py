from rest_framework import serializers

from .models import (
    Conversation,
    ConversationMessage,
    ConversationCapture
)
from apps.retailers.models import Retailer
from apps.catalogue.models import ProductVariant


class ConversationMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ConversationMessage
        fields = [
            "id",
            "sequence",
            "speaker",
            "message_type",
            "content",
            "confidence",
            "intent",
            "extracted_data",
            "created_at"
        ]
        read_only_fields = ["id", "sequence", "created_at"]


class ConversationCaptureSerializer(serializers.ModelSerializer):

    variant_name = serializers.CharField(
        source="variant.variant_name",
        read_only=True
    )

    product_name = serializers.CharField(
        source="variant.product.name",
        read_only=True
    )

    sku = serializers.CharField(
        source="variant.sku",
        read_only=True
    )

    class Meta:
        model = ConversationCapture
        fields = [
            "id",
            "variant",
            "variant_name",
            "product_name",
            "sku",
            "capture_type",
            "quantity",
            "notes",
            "status",
            "created_at",
            "updated_at"
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at"
        ]

    def validate_variant(self, value):
        if not value.is_active or not value.product.is_active:
            raise serializers.ValidationError(
                "The selected product variant is inactive."
            )
        return value


class ConversationSerializer(serializers.ModelSerializer):

    retailer_name = serializers.CharField(
        source="retailer.name",
        read_only=True
    )

    retailer_code = serializers.CharField(
        source="retailer.retailer_code",
        read_only=True
    )

    messages = ConversationMessageSerializer(many=True, read_only=True)
    captures = ConversationCaptureSerializer(many=True, read_only=True)

    message_count = serializers.IntegerField(
        source="messages.count",
        read_only=True
    )

    class Meta:
        model = Conversation
        fields = [
            "id",
            "retailer",
            "retailer_name",
            "retailer_code",
            "handled_by",
            "channel",
            "language",
            "status",
            "outcome",
            "summary",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
            "message_count",
            "messages",
            "captures"
        ]
        read_only_fields = [
            "id",
            "handled_by",
            "status",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at"
        ]

    def validate_retailer(self, value):
        if value.business_status != "ACTIVE":
            raise serializers.ValidationError(
                "Cannot start a conversation with an inactive retailer."
            )
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status in [
            Conversation.Status.COMPLETED,
            Conversation.Status.FAILED
        ]:
            raise serializers.ValidationError(
                "A closed conversation cannot be modified."
            )
        return attrs


class StartConversationSerializer(serializers.Serializer):

    retailer_id = serializers.IntegerField(min_value=1)

    channel = serializers.ChoiceField(
        choices=Conversation.Channel.choices,
        default=Conversation.Channel.VOICE
    )

    language = serializers.ChoiceField(
        choices=Conversation.Language.choices,
        default=Conversation.Language.ENGLISH
    )

    def validate_retailer_id(self, value):
        try:
            retailer = Retailer.objects.get(
                id=value,
                business_status=Retailer.BusinessStatus.ACTIVE
            )
        except Retailer.DoesNotExist:
            raise serializers.ValidationError(
                "Active retailer not found."
            )

        return retailer


class AddMessageSerializer(serializers.Serializer):

    speaker = serializers.ChoiceField(
        choices=ConversationMessage.Speaker.choices
    )

    message_type = serializers.ChoiceField(
        choices=ConversationMessage.MessageType.choices,
        default=ConversationMessage.MessageType.VOICE
    )

    content = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True
    )

    confidence = serializers.DecimalField(
        max_digits=4,
        decimal_places=3,
        min_value=0,
        max_value=1,
        required=False,
        allow_null=True
    )

    intent = serializers.CharField(required=False, allow_blank=True)

    extracted_data = serializers.JSONField(required=False)


class CompleteConversationSerializer(serializers.Serializer):

    outcome = serializers.ChoiceField(
        choices=Conversation.Outcome.choices,
        default=Conversation.Outcome.NO_ACTION
    )

    summary = serializers.CharField(
        required=False,
        allow_blank=True
    )