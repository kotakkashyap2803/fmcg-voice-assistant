from django.shortcuts import render

# Create your views here.
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.dateparse import parse_datetime

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.followups.models import FollowUp
from apps.followups.serializers import (
    FollowUpSerializer,
    FollowUpActivitySerializer,
    CreateFollowUpSerializer,
    RescheduleFollowUpSerializer,
    CompleteFollowUpSerializer,
    CancelFollowUpSerializer,
    FollowUpNoteSerializer,
)
from apps.followups.services import FollowUpService


class FollowUpViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Follow-up listing, retrieval, creation and lifecycle operations.
    """

    serializer_class = FollowUpSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Keep overdue statuses up to date whenever follow-ups are listed.
        FollowUpService.refresh_overdue()

        queryset = FollowUp.objects.select_related(
            "retailer",
            "conversation",
            "order",
            "assigned_to",
            "created_by",
        ).prefetch_related("activities")

        params = self.request.query_params

        retailer_id = params.get("retailer_id")
        assigned_to = params.get("assigned_to")
        priority = params.get("priority")
        followup_type = params.get("type")
        followup_status = params.get("status")
        outcome = params.get("outcome")
        search = params.get("search")

        if retailer_id:
            queryset = queryset.filter(retailer_id=retailer_id)

        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        if priority:
            queryset = queryset.filter(priority=priority.upper())

        if followup_type:
            queryset = queryset.filter(
                followup_type=followup_type.upper()
            )

        if followup_status:
            queryset = queryset.filter(
                status=followup_status.upper()
            )

        if outcome:
            queryset = queryset.filter(outcome=outcome.upper())

        if search:
            queryset = queryset.filter(
                title__icontains=search
            ) | queryset.filter(
                retailer__name__icontains=search
            ) | queryset.filter(
                retailer__shop_name__icontains=search
            ) | queryset.filter(
                retailer__primary_phone__icontains=search
            )

        due_from = params.get("due_from")
        due_to = params.get("due_to")

        if due_from:
            parsed = parse_datetime(due_from)
            if not parsed:
                raise ValidationError({
                    "due_from": "Use a valid ISO 8601 datetime."
                })
            queryset = queryset.filter(due_at__gte=parsed)

        if due_to:
            parsed = parse_datetime(due_to)
            if not parsed:
                raise ValidationError({
                    "due_to": "Use a valid ISO 8601 datetime."
                })
            queryset = queryset.filter(due_at__lte=parsed)

        return queryset.distinct()

    @staticmethod
    def handle_service_error(exc):
        if isinstance(exc, DjangoValidationError):
            if hasattr(exc, "message_dict"):
                detail = exc.message_dict
            else:
                detail = exc.messages

            raise ValidationError(detail)

        raise exc

    def create(self, request, *args, **kwargs):
        serializer = CreateFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            followup = FollowUpService.create_followup(
                data=serializer.validated_data,
                user=request.user,
            )
        except DjangoValidationError as exc:
            self.handle_service_error(exc)

        output = FollowUpSerializer(
            followup,
            context={"request": request}
        )

        return Response(
            output.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        serializer = RescheduleFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            followup = FollowUpService.reschedule(
                followup_id=pk,
                new_due_at=serializer.validated_data["due_at"],
                user=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            self.handle_service_error(exc)

        return Response(
            FollowUpSerializer(followup).data
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        serializer = CompleteFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            followup = FollowUpService.complete(
                followup_id=pk,
                outcome=serializer.validated_data["outcome"],
                outcome_notes=serializer.validated_data.get(
                    "outcome_notes", ""
                ),
                user=request.user,
            )
        except DjangoValidationError as exc:
            self.handle_service_error(exc)

        return Response(
            FollowUpSerializer(followup).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = CancelFollowUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            followup = FollowUpService.cancel(
                followup_id=pk,
                user=request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            self.handle_service_error(exc)

        return Response(
            FollowUpSerializer(followup).data
        )

    @action(detail=True, methods=["post"])
    def notes(self, request, pk=None):
        serializer = FollowUpNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            followup = FollowUpService.add_note(
                followup_id=pk,
                note=serializer.validated_data["note"],
                user=request.user,
            )
        except DjangoValidationError as exc:
            self.handle_service_error(exc)

        return Response(
            FollowUpSerializer(followup).data
        )

    @action(detail=True, methods=["get"])
    def activities(self, request, pk=None):
        followup = self.get_object()

        activities = followup.activities.select_related(
            "performed_by"
        ).all()

        serializer = FollowUpActivitySerializer(
            activities,
            many=True
        )

        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="refresh-overdue")
    def refresh_overdue(self, request):
        updated_count = FollowUpService.refresh_overdue()

        return Response({
            "message": "Overdue follow-ups refreshed successfully.",
            "updated_count": updated_count,
        })