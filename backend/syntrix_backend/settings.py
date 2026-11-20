import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only-change-this")
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in {"1", "true", "yes"}
if not DEBUG and SECRET_KEY in {
    "local-development-only-change-this",
    "replace-with-a-long-random-secret",
}:
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY in the project-root .env before running outside debug mode."
    )
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]
if DEBUG:
    for local_host in ("127.0.0.1", "localhost"):
        if local_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(local_host)

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_PATH = "/"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_USE_SESSIONS = False
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend(
        origin
        for origin in ("http://127.0.0.1:8000", "http://localhost:8000")
        if origin not in CSRF_TRUSTED_ORIGINS
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "syntrix_backend.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "syntrix_backend.wsgi.application"
ASGI_APPLICATION = "syntrix_backend.asgi.application"

DB_NAME = os.getenv("DB_NAME", "syntrix_ai")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
TEST_SETTINGS = os.getenv("DJANGO_SETTINGS_MODULE") == "syntrix_backend.test_settings"
USE_SQLITE = os.getenv("DJANGO_USE_SQLITE", "False").strip().lower() in {
    "1",
    "true",
    "yes",
}
PASSWORD_PLACEHOLDERS = {
    "your_actual_mysql_password",
    "your_actual_password",
    "replace-with-your-mysql-password",
}

if USE_SQLITE and not DEBUG:
    raise ImproperlyConfigured(
        "DJANGO_USE_SQLITE is for local development only; set DJANGO_DEBUG=True."
    )

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif DATABASE_URL:
    parsed_database_url = urlparse(DATABASE_URL)
    database_name = unquote(parsed_database_url.path.lstrip("/"))
    if not parsed_database_url.hostname or not database_name:
        raise ImproperlyConfigured(
            "DATABASE_URL must include a database name and hostname."
        )

    database_options = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
    }
    if parsed_database_url.scheme in {"postgres", "postgresql"}:
        database_engine = "django.db.backends.postgresql"
        sslmode = parse_qs(parsed_database_url.query).get("sslmode")
        if sslmode:
            database_options["sslmode"] = sslmode[-1]
    elif parsed_database_url.scheme in {"mysql", "mysql2"}:
        database_engine = "django.db.backends.mysql"
        database_options["charset"] = "utf8mb4"
    else:
        raise ImproperlyConfigured(
            "DATABASE_URL must use the postgres, postgresql, or mysql scheme."
        )

    DATABASES = {
        "default": {
            "ENGINE": database_engine,
            "NAME": database_name,
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname,
            "PORT": parsed_database_url.port
            or ("5432" if database_engine.endswith("postgresql") else "3306"),
            "OPTIONS": database_options,
        }
    }
else:
    if not TEST_SETTINGS and (
        not DB_USER
        or not DB_PASSWORD
        or not DB_PASSWORD.strip()
        or DB_PASSWORD.strip().lower() in PASSWORD_PLACEHOLDERS
    ):
        raise ImproperlyConfigured(
            "Set DB_USER and a real, non-empty DB_PASSWORD in backend/.env or the environment."
        )

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "OPTIONS": {
                "charset": "utf8mb4",
                "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
            },
        }
    }

AUTH_USER_MODEL = "accounts.User"
CONN_MAX_AGE = int(os.getenv("DB_CONN_MAX_AGE", "60"))
CONN_HEALTH_CHECKS = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = Path(os.getenv("STATIC_ROOT") or BASE_DIR / "staticfiles")
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT") or BASE_DIR / "private_media")
MAX_DOCUMENT_UPLOAD_BYTES = int(
    os.getenv("MAX_DOCUMENT_UPLOAD_BYTES", str(10 * 1024 * 1024))
)
