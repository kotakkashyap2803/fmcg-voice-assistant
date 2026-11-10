from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.followups.models import FollowUp, FollowUpActivity


class FollowUpService:

    @staticmethod
    @transaction.atomic
    def create_followup(data, user=None):
        followup = FollowUp.objects.create(
            **data,
            created_by=user
        )

        FollowUpActivity.objects.create(
            followup=followup,
            activity_type=FollowUpActivity.ActivityType.CREATED,
            description="Follow-up scheduled.",
            new_due_at=followup.due_at,
            new_status=followup.status,
            performed_by=user,
        )

        return followup

    @staticmethod
    def get_locked_followup(followup_id):
        try:
            return FollowUp.objects.select_for_update().get(
                id=followup_id
            )
        except FollowUp.DoesNotExist:
            raise ValidationError("Follow-up not found.")

    @staticmethod
    def ensure_actionable(followup):
        if followup.status not in [
            FollowUp.Status.PENDING,
            FollowUp.Status.OVERDUE,
        ]:
            raise ValidationError(
                f"Cannot perform this action on a {followup.status.lower()} follow-up."
            )

    @staticmethod
    @transaction.atomic
    def reschedule(followup_id, new_due_at, user=None, reason=""):
        followup = FollowUpService.get_locked_followup(followup_id)
        FollowUpService.ensure_actionable(followup)

        old_due_at = followup.due_at
        old_status = followup.status

        followup.due_at = new_due_at
        followup.status = (
            FollowUp.Status.OVERDUE
            if new_due_at <= timezone.now()
            else FollowUp.Status.PENDING
        )
        followup.save(update_fields=[
            "due_at",
            "status",
            "updated_at",
        ])

        FollowUpActivity.objects.create(
            followup=followup,
            activity_type=FollowUpActivity.ActivityType.RESCHEDULED,
            description=reason or "Follow-up rescheduled.",
            old_due_at=old_due_at,
            new_due_at=new_due_at,
            old_status=old_status,
            new_status=followup.status,
            performed_by=user,
        )

        return followup

    @staticmethod
    @transaction.atomic
    def complete(followup_id, outcome, outcome_notes="", user=None):
        followup = FollowUpService.get_locked_followup(followup_id)
        FollowUpService.ensure_actionable(followup)

        old_status = followup.status

        followup.status = FollowUp.Status.COMPLETED
        followup.outcome = outcome
        followup.outcome_notes = outcome_notes
        followup.completed_at = timezone.now()

        followup.save(update_fields=[
            "status",
            "outcome",
            "outcome_notes",
            "completed_at",
            "updated_at",
        ])

        FollowUpActivity.objects.create(
            followup=followup,
            activity_type=FollowUpActivity.ActivityType.COMPLETED,
            description=outcome_notes or f"Follow-up completed: {outcome}.",
            old_status=old_status,
            new_status=followup.status,
            performed_by=user,
            metadata={"outcome": outcome},
        )

        return followup

    @staticmethod
    @transaction.atomic
    def cancel(followup_id, user=None, reason=""):
        followup = FollowUpService.get_locked_followup(followup_id)
        FollowUpService.ensure_actionable(followup)

        old_status = followup.status

        followup.status = FollowUp.Status.CANCELLED
        followup.cancelled_at = timezone.now()

        followup.save(update_fields=[
            "status",
            "cancelled_at",
            "updated_at",
        ])

        FollowUpActivity.objects.create(
            followup=followup,
            activity_type=FollowUpActivity.ActivityType.CANCELLED,
            description=reason or "Follow-up cancelled.",
            old_status=old_status,
            new_status=followup.status,
            performed_by=user,
        )

        return followup

    @staticmethod
    @transaction.atomic
    def add_note(followup_id, note, user=None):
        followup = FollowUpService.get_locked_followup(followup_id)

        FollowUpActivity.objects.create(
            followup=followup,
            activity_type=FollowUpActivity.ActivityType.NOTE_ADDED,
            description=note,
            performed_by=user,
        )

        return followup

    @staticmethod
    @transaction.atomic
    def refresh_overdue():
        now = timezone.now()

        overdue_followups = FollowUp.objects.select_for_update().filter(
            status=FollowUp.Status.PENDING,
            due_at__lte=now
        )

        updated_count = 0

        for followup in overdue_followups:
            followup.status = FollowUp.Status.OVERDUE
            followup.save(update_fields=["status", "updated_at"])

            FollowUpActivity.objects.create(
                followup=followup,
                activity_type=FollowUpActivity.ActivityType.STATUS_CHANGED,
                description="Follow-up automatically marked as overdue.",
                old_status=FollowUp.Status.PENDING,
                new_status=FollowUp.Status.OVERDUE,
            )

            updated_count += 1

        return updated_count