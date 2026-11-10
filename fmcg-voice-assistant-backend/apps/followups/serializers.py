from rest_framework import serializers

from apps.followups.models import FollowUp, FollowUpActivity


class FollowUpActivitySerializer(serializers.ModelSerializer):
    performed_by_name = serializers.CharField(
        source="performed_by.username",
        read_only=True,
        default=None
    )

    class Meta:
        model = FollowUpActivity
        fields = [
            "id",
            "activity_type",
            "description",
            "old_due_at",
            "new_due_at",
            "old_status",
            "new_status",
            "performed_by",
            "performed_by_name",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class FollowUpSerializer(serializers.ModelSerializer):
    retailer_name = serializers.CharField(
        source="retailer.name",
        read_only=True
    )
    assigned_to_name = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
        default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.username",
        read_only=True,
        default=None
    )
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = FollowUp
        fields = [
            "id",
            "retailer",
            "retailer_name",
            "conversation",
            "order",
            "assigned_to",
            "assigned_to_name",
            "created_by",
            "created_by_name",
            "followup_type",
            "priority",
            "status",
            "outcome",
            "title",
            "description",
            "due_at",
            "outcome_notes",
            "completed_at",
            "cancelled_at",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "status",
            "outcome",
            "outcome_notes",
            "completed_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]

    def get_is_overdue(self, obj):
        from django.utils import timezone

        return (
            obj.status in [
                FollowUp.Status.PENDING,
                FollowUp.Status.OVERDUE,
            ]
            and obj.due_at <= timezone.now()
        )

    def validate(self, attrs):
        retailer = attrs.get(
            "retailer",
            getattr(self.instance, "retailer", None)
        )
        conversation = attrs.get(
            "conversation",
            getattr(self.instance, "conversation", None)
        )
        order = attrs.get(
            "order",
            getattr(self.instance, "order", None)
        )

        if conversation and retailer:
            if conversation.retailer_id != retailer.id:
                raise serializers.ValidationError({
                    "conversation": "Conversation does not belong to this retailer."
                })

        if order and retailer:
            if order.retailer_id != retailer.id:
                raise serializers.ValidationError({
                    "order": "Order does not belong to this retailer."
                })

        return attrs


class CreateFollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = [
            "retailer",
            "conversation",
            "order",
            "assigned_to",
            "followup_type",
            "priority",
            "title",
            "description",
            "due_at",
        ]

    def validate(self, attrs):
        retailer = attrs["retailer"]
        conversation = attrs.get("conversation")
        order = attrs.get("order")

        if retailer.business_status != "ACTIVE":
            raise serializers.ValidationError({
                "retailer": "Cannot schedule a follow-up for an inactive or blocked retailer."
            })

        if conversation and conversation.retailer_id != retailer.id:
            raise serializers.ValidationError({
                "conversation": "Conversation does not belong to this retailer."
            })

        if order and order.retailer_id != retailer.id:
            raise serializers.ValidationError({
                "order": "Order does not belong to this retailer."
            })

        return attrs


class RescheduleFollowUpSerializer(serializers.Serializer):
    due_at = serializers.DateTimeField()
    reason = serializers.CharField(
        required=False,
        allow_blank=True
    )


class CompleteFollowUpSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=FollowUp.Outcome.choices
    )
    outcome_notes = serializers.CharField(
        required=False,
        allow_blank=True
    )


class CancelFollowUpSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        allow_blank=True
    )


class FollowUpNoteSerializer(serializers.Serializer):
    note = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True
    )