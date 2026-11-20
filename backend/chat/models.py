from django.conf import settings
from django.db import models
from django.utils import timezone
from uuid import uuid4

from .validators import validate_document_file


def private_document_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"documents/{instance.user_id}/{uuid4().hex}.{extension[:10]}"


class Conversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    title = models.CharField(max_length=120, default="New conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        db_table = "conversations"
        indexes = [
            models.Index(
                fields=["user", "-updated_at"],
                name="conv_user_updated_idx",
            ),
        ]

    def __str__(self):
        return self.title


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        db_table = "messages"
        indexes = [
            models.Index(
                fields=["conversation", "created_at"],
                name="msg_conv_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"


class UploadedDocument(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        related_name="documents",
        null=True,
        blank=True,
    )
    original_name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=private_document_upload_path,
        validators=[validate_document_file],
    )
    content_type = models.CharField(max_length=127, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=12,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "uploaded_documents"
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="doc_user_created_idx",
            ),
        ]

    def __str__(self):
        return self.original_name


class AIUsageLog(models.Model):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_usage_logs",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        related_name="usage_logs",
        null=True,
        blank=True,
    )
    provider = models.CharField(max_length=32, default="openai")
    model = models.CharField(max_length=100)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.SUCCEEDED,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        db_table = "ai_usage_logs"
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="usage_user_created_idx",
            ),
            models.Index(
                fields=["conversation", "-created_at"],
                name="usage_conv_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.provider}/{self.model}: {self.status}"
