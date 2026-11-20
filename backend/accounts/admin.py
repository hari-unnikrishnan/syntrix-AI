from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from rest_framework.authtoken.models import TokenProxy

from .models import User, UserProfile, UserSettings


# The default DRF admin displays token keys, which are API credentials.
admin.site.unregister(TokenProxy)


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = AdminUserCreationForm
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "groups", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    date_hierarchy = "date_joined"
    list_per_page = 50
    readonly_fields = ("date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("username", "email", "first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "timezone", "created_at", "updated_at")
    list_filter = ("timezone", "created_at")
    search_fields = ("user__username", "user__email", "display_name", "bio")
    ordering = ("-updated_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Account", {"fields": ("user", "display_name", "bio", "timezone", "avatar_url")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "theme",
        "response_tone",
        "email_notifications",
        "updated_at",
    )
    list_filter = ("theme", "email_notifications", "created_at")
    search_fields = ("user__username", "user__email", "response_tone")
    ordering = ("-updated_at",)
    date_hierarchy = "created_at"
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Account", {"fields": ("user",)}),
        ("Preferences", {"fields": ("theme", "response_tone", "email_notifications")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
