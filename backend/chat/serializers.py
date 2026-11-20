from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from pathlib import PurePath
from rest_framework import serializers

from accounts.models import UserProfile, UserSettings

from .models import AIUsageLog, Conversation, Message, UploadedDocument
from .validators import validate_document_file

User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        validators=[validate_password],
    )

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is already in use.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("That email is already registered.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Incorrect username or password.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "date_joined",
        )
        read_only_fields = fields


DATABASE_RESOURCE_SORT_FIELDS = {
    "users": {
        "id", "-id", "username", "-username", "date_joined", "-date_joined",
    },
    "profiles": {
        "user__username", "-user__username", "created_at", "-created_at",
    },
    "settings": {
        "user__username", "-user__username", "created_at", "-created_at",
    },
    "conversations": {
        "title", "-title", "created_at", "-created_at", "updated_at", "-updated_at",
    },
    "messages": {
        "created_at", "-created_at", "role", "-role", "conversation_id", "-conversation_id",
    },
    "usage_logs": {
        "created_at", "-created_at", "model", "-model", "input_tokens", "-input_tokens",
    },
    "documents": {
        "created_at", "-created_at", "original_name", "-original_name", "size_bytes", "-size_bytes",
    },
}


class DatabaseResourceQuerySerializer(serializers.Serializer):
    resource = serializers.ChoiceField(
        choices=(
            "overview",
            "users",
            "profiles",
            "settings",
            "conversations",
            "messages",
            "usage_logs",
            "documents",
        ),
        required=False,
        default="overview",
    )
    search = serializers.CharField(required=False, allow_blank=True, max_length=100)
    page = serializers.IntegerField(required=False, min_value=1, max_value=1000000)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=50)
    sort = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def to_internal_value(self, data):
        unknown = set(data.keys()) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {"query": f"Unsupported parameter(s): {', '.join(sorted(unknown))}."}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        resource = attrs.get("resource", "overview")
        sort = attrs.get("sort", "")
        if resource == "overview" and any(
            key in attrs for key in ("search", "page", "page_size", "sort")
        ):
            raise serializers.ValidationError(
                "Pagination, search, and sorting require a record resource."
            )
        if sort and sort not in DATABASE_RESOURCE_SORT_FIELDS.get(resource, set()):
            raise serializers.ValidationError(
                {"sort": "Unsupported sort field for this resource."}
            )
        return attrs


class DatabaseUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    account_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "username",
            "email",
            "date_joined",
            "account_status",
        )
        read_only_fields = fields

    def get_full_name(self, user):
        return user.get_full_name()

    def get_account_status(self, user):
        return "active" if user.is_active else "disabled"


class DatabaseUserProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = (
            "user_id",
            "full_name",
            "display_name",
            "bio",
            "timezone",
            "avatar_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_full_name(self, profile):
        return profile.user.get_full_name() or profile.user.get_username()


class DatabaseUserSettingsSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserSettings
        fields = (
            "user_id",
            "user_name",
            "theme",
            "response_tone",
            "email_notifications",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DatabaseConversationSerializer(serializers.ModelSerializer):
    conversation_id = serializers.IntegerField(source="id", read_only=True)
    user_name = serializers.SerializerMethodField()
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = (
            "conversation_id",
            "user_name",
            "title",
            "message_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_user_name(self, conversation):
        return conversation.user.get_full_name() or conversation.user.get_username()


class DatabaseMessageSerializer(serializers.ModelSerializer):
    message_id = serializers.IntegerField(source="id", read_only=True)
    conversation_id = serializers.IntegerField(read_only=True)
    user_name = serializers.SerializerMethodField()
    message_type = serializers.CharField(source="role", read_only=True)

    class Meta:
        model = Message
        fields = (
            "message_id",
            "conversation_id",
            "user_name",
            "content",
            "message_type",
            "created_at",
        )
        read_only_fields = fields

    def get_user_name(self, message):
        user = message.conversation.user
        return user.get_full_name() or user.get_username()


class DatabaseAIUsageLogSerializer(serializers.ModelSerializer):
    log_id = serializers.IntegerField(source="id", read_only=True)
    user_name = serializers.SerializerMethodField()
    model_name = serializers.CharField(source="model", read_only=True)
    total_tokens = serializers.SerializerMethodField()

    class Meta:
        model = AIUsageLog
        fields = (
            "log_id",
            "user_name",
            "model_name",
            "provider",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "status",
            "created_at",
        )
        read_only_fields = fields

    def get_user_name(self, usage_log):
        return usage_log.user.get_full_name() or usage_log.user.get_username()

    def get_total_tokens(self, usage_log):
        return usage_log.input_tokens + usage_log.output_tokens


class DatabaseUploadedDocumentSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(source="id", read_only=True)
    user_name = serializers.SerializerMethodField()
    file_name = serializers.CharField(source="original_name", read_only=True)
    file_type = serializers.CharField(source="content_type", read_only=True)
    uploaded_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = UploadedDocument
        fields = (
            "document_id",
            "user_name",
            "file_name",
            "file_type",
            "size_bytes",
            "status",
            "uploaded_at",
        )
        read_only_fields = fields

    def get_user_name(self, document):
        return document.user.get_full_name() or document.user.get_username()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "display_name",
            "bio",
            "timezone",
            "avatar_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            "theme",
            "response_tone",
            "email_notifications",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "created_at")
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "created_at", "updated_at", "message_count")
        read_only_fields = fields

class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=8000, trim_whitespace=True)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_message(self, value):
        if not value:
            raise serializers.ValidationError("Message cannot be empty.")
        return value


class UploadedDocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    conversation = serializers.PrimaryKeyRelatedField(
        queryset=Conversation.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UploadedDocument
        fields = (
            "id",
            "original_name",
            "file",
            "content_type",
            "size_bytes",
            "status",
            "conversation",
            "created_at",
        )
        read_only_fields = (
            "id",
            "original_name",
            "content_type",
            "size_bytes",
            "status",
            "created_at",
        )

    def validate_conversation(self, conversation):
        request = self.context.get("request")
        if conversation and request and conversation.user_id != request.user.id:
            raise serializers.ValidationError(
                "The conversation does not belong to your account."
            )
        return conversation

    def validate_file(self, uploaded_file):
        try:
            validate_document_file(uploaded_file)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return uploaded_file

    def create(self, validated_data):
        uploaded_file = validated_data["file"]
        validated_data.update(
            original_name=PurePath(uploaded_file.name).name[:255],
            content_type=(getattr(uploaded_file, "content_type", "") or "")[:127],
            size_bytes=uploaded_file.size,
            user=self.context["request"].user,
        )
        return super().create(validated_data)
