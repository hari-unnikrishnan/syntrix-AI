from pathlib import Path

from django import forms
from django.contrib import admin
from django.db.models import Count

from .models import AIUsageLog, Conversation, Message, UploadedDocument


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender",
        "role",
        "content_preview",
        "created_at",
    )
    list_filter = ("role", "created_at")
    search_fields = (
        "content",
        "conversation__title",
        "conversation__user__username",
        "conversation__user__email",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Message", {"fields": ("conversation", "role", "content")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )

    @admin.display(description="User / sender", ordering="conversation__user__username")
    def sender(self, obj):
        return obj.conversation.user

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:120]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "title",
        "created_at",
        "updated_at",
        "message_count",
    )
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__username", "user__email")
    ordering = ("-updated_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Conversation", {"fields": ("user", "title")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    inlines = (MessageInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _admin_message_count=Count("messages")
        )

    @admin.display(description="Messages", ordering="_admin_message_count")
    def message_count(self, obj):
        return obj._admin_message_count


class UploadedDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = UploadedDocument
        fields = "__all__"
        widgets = {"file": forms.FileInput}


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    form = UploadedDocumentAdminForm
    list_display = (
        "id",
        "user",
        "original_name",
        "file_type",
        "status",
        "size_bytes",
        "created_at",
    )
    list_filter = ("status", "content_type", "created_at")
    search_fields = ("original_name", "user__username", "user__email")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Document", {"fields": ("user", "conversation", "original_name", "file")}),
        ("Processing", {"fields": ("content_type", "size_bytes", "status")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="File type", ordering="content_type")
    def file_type(self, obj):
        return obj.content_type or (
            Path(obj.original_name).suffix.lstrip(".").upper() or "Unknown"
        )


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "provider",
        "model",
        "input_tokens",
        "output_tokens",
        "status",
        "created_at",
    )
    list_filter = ("provider", "status", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "model",
        "conversation__title",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Request", {"fields": ("user", "conversation", "provider", "model", "status")}),
        ("Token usage", {"fields": ("input_tokens", "output_tokens")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )
