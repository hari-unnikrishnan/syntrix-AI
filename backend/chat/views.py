from pathlib import Path

from django.conf import settings
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile, UserSettings

from .models import AIUsageLog, Conversation, Message, UploadedDocument
from .serializers import (
    ChatRequestSerializer,
    ConversationSerializer,
    DATABASE_RESOURCE_SORT_FIELDS,
    DatabaseAIUsageLogSerializer,
    DatabaseConversationSerializer,
    DatabaseMessageSerializer,
    DatabaseResourceQuerySerializer,
    DatabaseUploadedDocumentSerializer,
    DatabaseUserProfileSerializer,
    DatabaseUserSerializer,
    DatabaseUserSettingsSerializer,
    LoginSerializer,
    MessageSerializer,
    RegistrationSerializer,
    UploadedDocumentSerializer,
    UserSerializer,
    UserProfileSerializer,
    UserSettingsSerializer,
)
from .services import AIProviderUnavailable, generate_reply


DATABASE_RESOURCE_SEARCH_FIELDS = {
    "users": ("username", "email", "first_name", "last_name"),
    "profiles": ("user__username", "display_name", "bio"),
    "settings": ("user__username", "response_tone", "theme"),
    "conversations": ("title", "user__username", "user__first_name", "user__last_name"),
    "messages": (
        "content",
        "role",
        "conversation__user__username",
        "conversation__user__first_name",
        "conversation__user__last_name",
    ),
    "usage_logs": ("model", "provider", "user__username"),
    "documents": ("original_name", "content_type", "user__username"),
}
DATABASE_RESOURCE_DEFAULT_SORT = {
    "users": "-date_joined",
    "profiles": "user__username",
    "settings": "user__username",
    "conversations": "-updated_at",
    "messages": "-created_at",
    "usage_logs": "-created_at",
    "documents": "-created_at",
}
DATABASE_RESOURCE_SERIALIZERS = {
    "users": DatabaseUserSerializer,
    "profiles": DatabaseUserProfileSerializer,
    "settings": DatabaseUserSettingsSerializer,
    "conversations": DatabaseConversationSerializer,
    "messages": DatabaseMessageSerializer,
    "usage_logs": DatabaseAIUsageLogSerializer,
    "documents": DatabaseUploadedDocumentSerializer,
}


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "The AI provider is temporarily unavailable."
    default_code = "ai_provider_unavailable"


class DatabaseDashboardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


def get_database_snapshot():
    database_engine = connection.vendor
    database_name = str(connection.settings_dict["NAME"])
    if database_engine == "sqlite":
        database_name = Path(database_name).name

    connection.ensure_connection()
    tables = connection.introspection.table_names()
    models = sorted(
        apps.get_models(),
        key=lambda model: (model._meta.app_label, model.__name__),
    )
    model_details = [
        {
            "name": f"{model._meta.app_label}.{model.__name__}",
            "table": model._meta.db_table,
            "record_count": model._default_manager.using("default").count(),
        }
        for model in models
    ]
    return {
        "database": {
            "status": "connected",
            "name": database_name,
            "engine": database_engine,
        },
        "tables": tables,
        "models": model_details,
        "record_counts": {
            model["name"]: model["record_count"] for model in model_details
        },
    }


def get_database_identity():
    database_engine = connection.vendor
    database_name = str(connection.settings_dict["NAME"])
    if database_engine == "sqlite":
        database_name = Path(database_name).name
    connection.ensure_connection()
    return {
        "status": "connected",
        "name": database_name,
        "engine": database_engine,
    }


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            connection.ensure_connection()
        except DatabaseError:
            return Response(
                {
                    "status": "error",
                    "database": "unavailable",
                    "ai_mode": "live" if settings.OPENAI_API_KEY else "demo",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "status": "ok",
                "database": "connected",
                "ai_mode": "live" if settings.OPENAI_API_KEY else "demo",
            }
        )


class DatabaseDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            return Response(
                {
                    "status": "ok",
                    **get_database_snapshot(),
                    "ai_mode": "live" if settings.OPENAI_API_KEY else "demo",
                }
            )
        except DatabaseError:
            return Response(
                {"status": "error", "detail": "Database is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class DatabaseUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = get_user_model()._default_manager.all().order_by("id")
        search = request.query_params.get("search", "").strip()
        if search:
            users = users.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        paginator = DatabaseDashboardPagination()
        try:
            page = paginator.paginate_queryset(users, request, view=self)
            results = [
                {
                    "id": user.pk,
                    "full_name": user.get_full_name(),
                    "username": user.get_username(),
                    "email": user.email,
                    "created_at": user.date_joined,
                }
                for user in page
            ]
        except DatabaseError:
            return Response(
                {"detail": "Database is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return paginator.get_paginated_response(results)


class DatabaseConversationListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        conversations = Conversation.objects.select_related("user").annotate(
            message_count=Count("messages")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            conversations = conversations.filter(
                Q(title__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )
        conversations = conversations.order_by("-updated_at", "-pk")

        paginator = DatabaseDashboardPagination()
        try:
            page = paginator.paginate_queryset(conversations, request, view=self)
            results = [
                {
                    "chat_id": conversation.pk,
                    "user_name": (
                        conversation.user.get_full_name()
                        or conversation.user.get_username()
                    ),
                    "conversation_id": conversation.pk,
                    "message_count": conversation.message_count,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                }
                for conversation in page
            ]
        except DatabaseError:
            return Response(
                {"detail": "Database is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return paginator.get_paginated_response(results)


class AdminDatabaseView(APIView):
    permission_classes = [IsAdminUser]

    def get_queryset(self, resource):
        if resource == "users":
            return get_user_model()._default_manager.all()
        if resource == "profiles":
            return UserProfile.objects.select_related("user").all()
        if resource == "settings":
            return UserSettings.objects.select_related("user").all()
        if resource == "conversations":
            return Conversation.objects.select_related("user").annotate(
                message_count=Count("messages")
            )
        if resource == "messages":
            return Message.objects.select_related("conversation__user").all()
        if resource == "usage_logs":
            return AIUsageLog.objects.select_related("user").all()
        if resource == "documents":
            return UploadedDocument.objects.select_related("user").all()
        raise ValueError(f"Unknown database resource: {resource}")

    def get(self, request):
        query_serializer = DatabaseResourceQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                query_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = query_serializer.validated_data
        resource = params.get("resource", "overview")
        try:
            if resource == "overview":
                snapshot = get_database_snapshot()
                return Response(
                    {
                        "status": "ok",
                        **snapshot,
                        "summary": {
                            "users": get_user_model()._default_manager.count(),
                            "conversations": Conversation.objects.count(),
                            "messages": Message.objects.count(),
                            "documents": UploadedDocument.objects.count(),
                            "ai_usage_logs": AIUsageLog.objects.count(),
                        },
                        "ai_mode": "live" if settings.OPENAI_API_KEY else "demo",
                    }
                )

            database = get_database_identity()
            queryset = self.get_queryset(resource)
            search = params.get("search", "").strip()
            if search:
                search_query = Q()
                for field in DATABASE_RESOURCE_SEARCH_FIELDS[resource]:
                    search_query |= Q(**{f"{field}__icontains": search})
                queryset = queryset.filter(search_query)

            ordering = params.get("sort") or DATABASE_RESOURCE_DEFAULT_SORT[resource]
            queryset = queryset.order_by(ordering)
            paginator = DatabaseDashboardPagination()
            if "page_size" in params:
                paginator.page_size = params["page_size"]
            page = paginator.paginate_queryset(queryset, request, view=self)
            data = DATABASE_RESOURCE_SERIALIZERS[resource](page, many=True).data
            return Response(
                {
                    "status": "ok",
                    "database": database,
                    "resource": resource,
                    **paginator.get_paginated_response(data).data,
                }
            )
        except DatabaseError:
            return Response(
                {"status": "error", "detail": "Database is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.auth is not None:
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(UserProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
        return Response(UserSettingsSerializer(user_settings).data)

    def patch(self, request):
        user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(
            user_settings,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(user=request.user).annotate(
            message_count=Count("messages")
        )
        return Response(ConversationSerializer(conversations, many=True).data)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation.objects.filter(user=request.user).annotate(
                message_count=Count("messages")
            ),
            pk=conversation_id,
        )
        messages = conversation.messages.all()
        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "messages": MessageSerializer(messages, many=True).data,
            }
        )

    def delete(self, request, conversation_id):
        conversation = get_object_or_404(
            Conversation,
            pk=conversation_id,
            user=request.user,
        )
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadedDocumentListView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        documents = UploadedDocument.objects.filter(user=request.user)
        return Response(UploadedDocumentSerializer(documents, many=True).data)

    def post(self, request):
        serializer = UploadedDocumentSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(
            UploadedDocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class UploadedDocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        document = get_object_or_404(
            UploadedDocument,
            pk=document_id,
            user=request.user,
        )
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIUsageSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        summary = AIUsageLog.objects.filter(user=request.user).aggregate(
            requests=Count("id"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
        )
        return Response(
            {
                "requests": summary["requests"],
                "input_tokens": summary["input_tokens"] or 0,
                "output_tokens": summary["output_tokens"] or 0,
            }
        )


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message_text = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        if conversation_id is None:
            conversation = Conversation.objects.create(
                user=request.user,
                title=message_text[:80],
            )
        else:
            conversation = get_object_or_404(
                Conversation,
                pk=conversation_id,
                user=request.user,
            )

        user_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=message_text,
        )

        recent_messages = list(
            conversation.messages.order_by("-created_at", "-id")[:20]
        )
        history = [
            {"role": item.role, "content": item.content}
            for item in reversed(recent_messages)
        ]
        try:
            reply, mode, usage = generate_reply(history)
        except AIProviderUnavailable as exc:
            AIUsageLog.objects.create(
                user=request.user,
                conversation=conversation,
                provider="openai",
                model=settings.OPENAI_MODEL,
                status=AIUsageLog.Status.FAILED,
            )
            user_message.delete()
            if conversation_id is None:
                conversation.delete()
            raise ServiceUnavailable(str(exc)) from exc

        AIUsageLog.objects.create(
            user=request.user,
            conversation=conversation,
            provider="openai" if mode == "live" else "demo",
            model=settings.OPENAI_MODEL if mode == "live" else "demo",
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=reply,
        )
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "user_message": MessageSerializer(user_message).data,
                "assistant_message": MessageSerializer(assistant_message).data,
                "mode": mode,
            },
            status=status.HTTP_201_CREATED,
        )
