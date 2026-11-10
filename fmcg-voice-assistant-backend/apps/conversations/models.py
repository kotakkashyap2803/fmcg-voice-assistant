from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from apps.retailers.models import Retailer
from apps.catalogue.models import ProductVariant


class Conversation(models.Model):

    class Channel(models.TextChoices):
        VOICE = "VOICE", "Voice"
        WEB = "WEB", "Web"

    class Language(models.TextChoices):
        ENGLISH = "en", "English"
        HINDI = "hi", "Hindi"

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class Outcome(models.TextChoices):
        NO_ACTION = "NO_ACTION", "No Action"
        ENQUIRY = "ENQUIRY", "Product Enquiry"
        INTERESTED = "INTERESTED", "Interested"
        ORDER_REQUESTED = "ORDER_REQUESTED", "Order Requested"
        FOLLOWUP_REQUIRED = "FOLLOWUP_REQUIRED", "Follow-up Required"
        NOT_INTERESTED = "NOT_INTERESTED", "Not Interested"

    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.PROTECT,
        related_name="conversations"
    )

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_conversations"
    )

    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.VOICE
    )

    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.ENGLISH
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.INITIATED
    )

    outcome = models.CharField(
        max_length=25,
        choices=Outcome.choices,
        default=Outcome.NO_ACTION
    )

    summary = models.TextField(blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["retailer", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
            models.Index(fields=["outcome"]),
        ]

    def __str__(self):
        return f"Conversation #{self.id} - {self.retailer.name}"


class ConversationMessage(models.Model):

    class Speaker(models.TextChoices):
        RETAILER = "RETAILER", "Retailer"
        AGENT = "AGENT", "AI Agent"
        SYSTEM = "SYSTEM", "System"

    class MessageType(models.TextChoices):
        VOICE = "VOICE", "Voice"
        TEXT = "TEXT", "Text"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sequence = models.PositiveIntegerField()

    speaker = models.CharField(
        max_length=10,
        choices=Speaker.choices
    )

    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.VOICE
    )

    content = models.TextField()

    # Optional transcription confidence, between 0 and 1.
    confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0)
        ]
    )

    # Structured AI extraction, not the source transcript.
    intent = models.CharField(max_length=100, blank=True)

    extracted_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "conversation_messages"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence"],
                name="unique_conversation_message_sequence"
            )
        ]

    def __str__(self):
        return f"{self.conversation_id} - {self.speaker} - {self.sequence}"


class ConversationCapture(models.Model):

    class CaptureType(models.TextChoices):
        ENQUIRY = "ENQUIRY", "Enquiry"
        INTEREST = "INTEREST", "Product Interest"
        ORDER_INTENT = "ORDER_INTENT", "Order Intent"

    class CaptureStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        CONVERTED = "CONVERTED", "Converted"
        DECLINED = "DECLINED", "Declined"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="captures"
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="conversation_captures"
    )

    capture_type = models.CharField(
        max_length=15,
        choices=CaptureType.choices
    )

    quantity = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=15,
        choices=CaptureStatus.choices,
        default=CaptureStatus.OPEN
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversation_captures"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "capture_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.capture_type} - Conversation {self.conversation_id}"