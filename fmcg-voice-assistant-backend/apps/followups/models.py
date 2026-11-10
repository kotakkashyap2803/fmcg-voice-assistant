from django.db import models

# Create your models here.
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class FollowUp(models.Model):

    class FollowUpType(models.TextChoices):
        CALL = "CALL", "Call"
        VISIT = "VISIT", "Visit"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        EMAIL = "EMAIL", "Email"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        OVERDUE = "OVERDUE", "Overdue"

    class Outcome(models.TextChoices):
        INTERESTED = "INTERESTED", "Interested"
        NOT_INTERESTED = "NOT_INTERESTED", "Not Interested"
        ORDER_PLACED = "ORDER_PLACED", "Order Placed"
        CALLBACK_REQUIRED = "CALLBACK_REQUIRED", "Callback Required"
        NO_RESPONSE = "NO_RESPONSE", "No Response"
        OTHER = "OTHER", "Other"

    retailer = models.ForeignKey(
        "retailers.Retailer",
        on_delete=models.PROTECT,
        related_name="followups"
    )

    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups"
    )

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followups"
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_followups"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_followups"
    )

    followup_type = models.CharField(
        max_length=20,
        choices=FollowUpType.choices,
        default=FollowUpType.CALL
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    outcome = models.CharField(
        max_length=25,
        choices=Outcome.choices,
        null=True,
        blank=True
    )

    title = models.CharField(max_length=200)

    description = models.TextField(blank=True)

    due_at = models.DateTimeField(db_index=True)

    outcome_notes = models.TextField(blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "followups"
        ordering = ["due_at", "-priority"]
        indexes = [
            models.Index(
                fields=["status", "due_at"],
                name="followup_status_due_idx"
            ),
            models.Index(
                fields=["retailer", "status"],
                name="followup_retailer_status_idx"
            ),
            models.Index(
                fields=["assigned_to", "status"],
                name="followup_assignee_status_idx"
            ),
        ]

    def clean(self):
        errors = {}

        if self.conversation_id and self.retailer_id:
            if self.conversation.retailer_id != self.retailer_id:
                errors["conversation"] = (
                    "The selected conversation does not belong to this retailer."
                )

        if self.order_id and self.retailer_id:
            if self.order.retailer_id != self.retailer_id:
                errors["order"] = (
                    "The selected order does not belong to this retailer."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.title} - {self.retailer}"


class FollowUpActivity(models.Model):

    class ActivityType(models.TextChoices):
        CREATED = "CREATED", "Created"
        NOTE_ADDED = "NOTE_ADDED", "Note Added"
        RESCHEDULED = "RESCHEDULED", "Rescheduled"
        ASSIGNED = "ASSIGNED", "Assigned"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"

    followup = models.ForeignKey(
        FollowUp,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices
    )

    description = models.TextField()

    old_due_at = models.DateTimeField(null=True, blank=True)

    new_due_at = models.DateTimeField(null=True, blank=True)

    old_status = models.CharField(max_length=15, blank=True)

    new_status = models.CharField(max_length=15, blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="followup_activities"
    )

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "followup_activities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["followup", "created_at"],
                name="followup_activity_time_idx"
            )
        ]

    def __str__(self):
        return f"{self.followup_id} - {self.activity_type}"