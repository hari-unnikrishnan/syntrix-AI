from pathlib import Path

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError, connection
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

from accounts.models import User, UserProfile, UserSettings
from chat.models import AIUsageLog, Conversation, Message, UploadedDocument


@staff_member_required
def database_dashboard(request):
    models = (
        User,
        UserProfile,
        UserSettings,
        Conversation,
        Message,
        AIUsageLog,
        UploadedDocument,
    )
    database_name = str(connection.settings_dict["NAME"])
    if connection.vendor == "sqlite":
        database_name = Path(database_name).name

    counts = {
        "users": 0,
        "conversations": 0,
        "messages": 0,
        "documents": 0,
        "ai_usage_logs": 0,
    }
    try:
        connection.ensure_connection()
        tables = connection.introspection.table_names()
        model_rows = []
        for model in models:
            admin_url = None
            if admin.site.is_registered(model):
                try:
                    admin_url = reverse(
                        f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
                    )
                except NoReverseMatch:
                    admin_url = None
            model_rows.append(
                {
                    "name": model._meta.verbose_name.title(),
                    "table": model._meta.db_table,
                    "count": model._default_manager.count(),
                    "admin_url": admin_url,
                }
            )
        counts = {
            "users": User.objects.count(),
            "conversations": Conversation.objects.count(),
            "messages": Message.objects.count(),
            "documents": UploadedDocument.objects.count(),
            "ai_usage_logs": AIUsageLog.objects.count(),
        }
        database_status = "connected"
    except DatabaseError:
        tables = []
        model_rows = []
        database_status = "unavailable"

    return render(
        request,
        "admin/database_dashboard.html",
        {
            **admin.site.each_context(request),
            "title": "Database overview",
            "database": {
                "status": database_status,
                "name": database_name,
                "engine": connection.vendor,
            },
            "tables": tables,
            "model_rows": model_rows,
            "counts": counts,
        },
    )
