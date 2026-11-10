from django.contrib import admin

# Register your models here.
from django.contrib import admin

from apps.followups.models import FollowUp, FollowUpActivity


class FollowUpActivityInline(admin.TabularInline):
    model = FollowUpActivity
    extra = 0
    can_delete = False
    readonly_fields = [
        "activity_type",
        "description",
        "old_due_at",
        "new_due_at",
        "old_status",
        "new_status",
        "performed_by",
        "metadata",
        "created_at",
    ]


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title",
        "retailer",
        "followup_type",
        "priority",
        "status",
        "assigned_to",
        "due_at",
    ]

    list_filter = [
        "status",
        "priority",
        "followup_type",
        "outcome",
    ]

    search_fields = [
        "title",
        "retailer__name",
        "retailer__shop_name",
        "retailer__primary_phone",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "completed_at",
        "cancelled_at",
    ]

    inlines = [FollowUpActivityInline]


@admin.register(FollowUpActivity)
class FollowUpActivityAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "followup",
        "activity_type",
        "performed_by",
        "created_at",
    ]

    list_filter = ["activity_type", "created_at"]

    search_fields = [
        "followup__title",
        "description",
    ]

    readonly_fields = [
        "followup",
        "activity_type",
        "description",
        "old_due_at",
        "new_due_at",
        "old_status",
        "new_status",
        "performed_by",
        "metadata",
        "created_at",
    ]