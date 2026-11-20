from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import RedirectView

from .admin_views import database_dashboard

urlpatterns = [
    path("", RedirectView.as_view(url="/api/health/", permanent=False), name="home"),
    path("admin/login/", ensure_csrf_cookie(admin.site.login), name="admin-login"),
    path(
        "admin/database/",
        admin.site.admin_view(database_dashboard),
        name="admin-database-dashboard",
    ),
    path("admin/", admin.site.urls),
    path("api/", include("chat.urls")),
]
