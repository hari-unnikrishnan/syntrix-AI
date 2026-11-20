from django.urls import path

from .views import (
    AdminDatabaseView,
    ChatView,
    ConversationDetailView,
    ConversationListView,
    CurrentUserView,
    DatabaseDashboardView,
    DatabaseConversationListView,
    DatabaseUserListView,
    HealthView,
    LoginView,
    RegisterView,
    AIUsageSummaryView,
    UploadedDocumentDetailView,
    UploadedDocumentListView,
    UserProfileView,
    UserSettingsView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("admin/database/", AdminDatabaseView.as_view(), name="admin-database"),
    path("database/", DatabaseDashboardView.as_view(), name="database-dashboard"),
    path("database/users/", DatabaseUserListView.as_view(), name="database-users"),
    path(
        "database/conversations/",
        DatabaseConversationListView.as_view(),
        name="database-conversations",
    ),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("auth/profile/", UserProfileView.as_view(), name="user-profile"),
    path("settings/", UserSettingsView.as_view(), name="user-settings"),
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<int:conversation_id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path("documents/", UploadedDocumentListView.as_view(), name="document-list"),
    path(
        "documents/<int:document_id>/",
        UploadedDocumentDetailView.as_view(),
        name="document-detail",
    ),
    path("usage/", AIUsageSummaryView.as_view(), name="ai-usage-summary"),
    path("chat/", ChatView.as_view(), name="chat"),
]
