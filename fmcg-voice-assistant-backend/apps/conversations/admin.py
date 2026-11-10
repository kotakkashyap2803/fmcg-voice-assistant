from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import (
    Conversation,
    ConversationMessage,
    ConversationCapture
)


class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    extra = 0
    readonly_fields = ("sequence", "created_at")
    ordering = ("sequence",)


class ConversationCaptureInline(admin.TabularInline):
    model = ConversationCapture
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "retailer",
        "channel",
        "language",
        "status",
        "outcome",
        "started_at"
    )

    list_filter = (
        "status",
        "outcome",
        "channel",
        "language"
    )

    search_fields = (
        "retailer__name",
        "retailer__retailer_code",
        "summary"
    )

    readonly_fields = (
        "started_at",
        "ended_at",
        "created_at",
        "updated_at"
    )

    inlines = [
        ConversationMessageInline,
        ConversationCaptureInline
    ]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):

    list_display = (
        "conversation",
        "sequence",
        "speaker",
        "message_type",
        "created_at"
    )

    list_filter = ("speaker", "message_type")
    search_fields = ("content", "intent")


@admin.register(ConversationCapture)
class ConversationCaptureAdmin(admin.ModelAdmin):

    list_display = (
        "conversation",
        "variant",
        "capture_type",
        "quantity",
        "status",
        "created_at"
    )

    list_filter = ("capture_type", "status")
    search_fields = ("notes",)