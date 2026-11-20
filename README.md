# Syntrix AI

Syntrix AI is an AI-powered workspace with a React/Vite frontend and a Django REST API. MySQL remains the default database; production can use PostgreSQL by setting `DATABASE_URL`, and local development can explicitly opt into SQLite. OpenAI requests run only on the backend; when `OPENAI_API_KEY` is empty, the chat clearly identifies its responses as demo mode.

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- MySQL 8+ for the default database, or PostgreSQL for production with `DATABASE_URL`; neither is required for local development when the SQLite option is enabled

## 1. Configure a database and environment

Create `backend/.env` from `backend/.env.example` only if it does not already exist; otherwise edit it in place. Keep `.env` private; it is ignored by Git. Add the OpenAI key to `OPENAI_API_KEY` on the backend only. Leave it empty to use the labelled demo mode; restart Django after changing the key.

### MySQL

Create a database and a dedicated local user in MySQL:

```sql
CREATE DATABASE IF NOT EXISTS syntrix_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'syntrix_user'@'localhost' IDENTIFIED BY 'choose-a-local-password';
GRANT ALL PRIVILEGES ON syntrix_ai.* TO 'syntrix_user'@'localhost';
```

Run the SQL as a MySQL administrator. `CREATE USER IF NOT EXISTS` does not change the password of an existing account; use that account's current password, and have an administrator handle any needed credential changes. Set `DB_NAME=syntrix_ai`, `DB_USER=syntrix_user`, `DB_PASSWORD` to that MySQL user's password, `DB_HOST=127.0.0.1`, and `DB_PORT=3306`. The backend loads `backend/.env` first and the project-root `.env` for other settings.

On Windows PowerShell, if `DB_USER` or `DB_PASSWORD` is already set in the shell, Django will use those process environment values ahead of `.env`. To use `backend/.env` instead, clear any inherited values in that terminal before running Django:

```powershell
Remove-Item Env:DB_USER -ErrorAction SilentlyContinue
Remove-Item Env:DB_PASSWORD -ErrorAction SilentlyContinue
```

The project uses Django's MySQL backend through the compatible PyMySQL driver by default. Django stops with a clear configuration error if `DB_USER` or a non-placeholder `DB_PASSWORD` is missing. `python manage.py migrate` creates and updates the schema; it does not create the MySQL database or MySQL account. Create those once using a MySQL administrative account, then use the restricted application account in `backend/.env`.

### PostgreSQL production option

Set `DATABASE_URL` to the PostgreSQL connection URL from your hosting provider (for example, `postgresql://USER:PASSWORD@HOST:5432/DB_NAME?sslmode=require`). URL-encoded credentials are supported. When present, it takes precedence over the MySQL `DB_*` settings. Keep the provider's URL private.

For local development only, set `DJANGO_DEBUG=True` and `DJANGO_USE_SQLITE=True` in `backend/.env`. Django then uses the existing `backend/db.sqlite3` and does not require MySQL credentials. This opt-in is rejected when `DJANGO_DEBUG` is false. Do not enable it in production. Django migrations create and update application tables; do not run a separate SQLite script or delete/reset migrations.

The chat service uses the OpenAI Responses API with `OPENAI_MODEL` (defaults to `gpt-5.1`). Set a valid `OPENAI_API_KEY` in `backend/.env` to enable live replies, then restart Django. Without a key, chat remains in clearly labelled demo mode. Invalid credentials, rate/usage limits, network timeouts, and other OpenAI request errors return safe actionable messages through the chat API; provider response details and credentials are not exposed.

After setting `.env`, apply migrations and verify the database with `GET /api/health/` (it returns `database: connected` only after Django has opened a database connection). Chat, registration, and the other database-backed APIs must not be used until this check succeeds.

The public health endpoint returns only application status, database connectivity, and AI mode. Staff users can inspect actual database metadata and records through the protected database dashboard API and frontend.

Generate a Django secret key with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy `frontend/.env.example` to `frontend/.env.local`. Set `VITE_API_URL` if the Django API is not at `http://127.0.0.1:8000/api`.

## 2. Start the Django API

In PowerShell, from the project root:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\manage.py migrate
.\backend\.venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000
```

The API is available at `http://127.0.0.1:8000/api/`. With the local SQLite option enabled, these commands use `backend/db.sqlite3`; otherwise they use the configured PostgreSQL URL or MySQL settings. The public health endpoint verifies the database connection before reporting the API ready. Register in the app to create an account. Passwords are stored using Django's password hashers. Optional admin access:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\manage.py createsuperuser
```

The admin login keeps Django CSRF protection enabled. The built-in admin login route explicitly ensures that a CSRF cookie is issued on GET; it is not exempt from CSRF validation. In local debug mode, cookies are configured for HTTP on `127.0.0.1` and `localhost`; in non-debug mode, CSRF and session cookies are marked secure for HTTPS. If the login POST has no CSRF cookie, reload the login page and ensure the browser accepts cookies for the same host. Django test-client regression tests verify cookie attributes, a successful CSRF-protected admin login, access to the admin index, and rejection of missing or invalid CSRF tokens.

## 3. Start the React app

In a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, create an account, and start a conversation. The API requires a migrated database; local development may use SQLite, while production should use PostgreSQL or MySQL.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health/` | API and AI mode status |
| `GET` | `/api/admin/database/` | Database connection, tables, models, record counts, and summary counts (staff only) |
| `GET` | `/api/admin/database/?resource=users&page=1&page_size=10` | Paginated user records; supported resources are `users`, `profiles`, `settings`, `conversations`, `messages`, `usage_logs`, and `documents` |
| `GET` | `/api/database/` | Database metadata, tables, models, and record counts (staff only) |
| `GET` | `/api/database/users/?search=&page=1&page_size=10` | Paginated user records (staff only; no passwords or tokens) |
| `GET` | `/api/database/conversations/?search=&page=1&page_size=10` | Paginated conversation summaries and message counts (staff only; no message content) |
| `POST` | `/api/auth/register/` | Create an account and token |
| `POST` | `/api/auth/login/` | Sign in and receive a token |
| `GET` | `/api/auth/me/` | Current account |
| `GET`, `PATCH` | `/api/auth/profile/` | Read or update the signed-in user's profile |
| `GET`, `PATCH` | `/api/settings/` | Read or update the signed-in user's settings |
| `GET` | `/api/conversations/` | List the signed-in user's conversations |
| `GET`, `DELETE` | `/api/conversations/{id}/` | Read or delete an owned conversation |
| `GET`, `POST` | `/api/documents/` | List or upload private PDF, DOCX, TXT, or MD documents |
| `DELETE` | `/api/documents/{id}/` | Delete an owned document and its stored file |
| `GET` | `/api/usage/` | Read the signed-in user's aggregate AI usage |
| `POST` | `/api/chat/` | Send a message and receive an AI/demo reply |

Protected endpoints use Django REST Framework token authentication. Conversation, document, profile, setting, and usage queries are scoped to the authenticated user. Document files are stored under private `MEDIA_ROOT` and are not exposed by a public media route. Uploads are limited by `MAX_DOCUMENT_UPLOAD_BYTES` (10 MiB by default) and accepted extensions. OpenAI and database credentials are never sent to the browser.

The admin database endpoint requires a staff account and supports `resource`, `search`, `page`, `page_size`, and resource-specific `sort` query parameters. Search is limited to 100 characters, page size to 50, and unsupported query parameters or sort fields are rejected. The default `resource=overview` response includes database metadata, table/model information, and summary counts; request a record resource for a paginated table. Message content and personal records are only returned to staff accounts, while passwords, tokens, and API keys are never serialized. The frontend shows the Database navigation item only to staff users. Django Admin also has a `Database overview` link on `/admin/` and a server-rendered summary at `/admin/database/`. All application models are registered for authorized administration; private document file paths and API token keys are not exposed in the admin. Create or promote a trusted administrator with Django's `createsuperuser` command; ordinary accounts cannot access these records.

## Database schema

| Table | Django model | Relationship and indexes |
| --- | --- | --- |
| `users` | `accounts.User` | Django `AbstractUser`; Django password hashing; unique username/email |
| `user_profiles` | `accounts.UserProfile` | One-to-one with `users` |
| `user_settings` | `accounts.UserSettings` | One-to-one with `users` |
| `conversations` | `chat.Conversation` | Foreign key to `users`; composite user/updated-time index |
| `messages` | `chat.Message` | Foreign key to `conversations`; composite conversation/created-time index |
| `uploaded_documents` | `chat.UploadedDocument` | Foreign keys to `users` and optional `conversations`; composite user/created-time index |
| `ai_usage_logs` | `chat.AIUsageLog` | Foreign keys to `users` and optional `conversations`; user/time and conversation/time indexes |

Migrations live in `backend/accounts/migrations` and `backend/chat/migrations`. Normal application reads and writes use Django ORM querysets. Conversation lists annotate message counts in SQL, and usage summaries use SQL aggregates rather than loading rows into application memory. Password fields use Django's password hashing; raw passwords are never saved.

## Tests and production notes

Run the backend checks and tests from `backend`:

```powershell
python manage.py check
python manage.py test
```

The test settings use an isolated SQLite test database and force demo AI mode; they do not use or replace `backend/db.sqlite3`. Build the frontend with `npm install` and `npm run build` from `frontend`.

## Production deployment

The Django API and admin require a Python host; GitHub Pages is static hosting only and cannot run Django, Python, or a database. This repository includes a GitHub Actions Pages workflow and a Render Blueprint, but neither hosting platform is provisioned automatically. The live Pages URL will serve the React app only after Pages is configured and the workflow succeeds.

### Deploy the backend to Render

1. Create a Render PostgreSQL database and a web service from this repository's `render.yaml`. The Blueprint's `DATABASE_URL` is intentionally unsynced: set it to the private PostgreSQL connection URL from the database you provisioned. The service must use a hostname matching `DJANGO_ALLOWED_HOSTS` in the Blueprint; update that environment value if Render assigns a different hostname.
2. Set `CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to the exact HTTPS frontend origin (for this repository: `https://hari-unnikrishnan.github.io`), and optionally set `OPENAI_API_KEY` to enable real AI responses. Keep provider credentials in Render's environment settings only.
3. Deploy. The manifest installs backend requirements, collects static files, runs migrations as its pre-deploy command, and starts Gunicorn. Verify `https://<your-backend-host>/api/health/` reports a connected database, then create an administrator from the Render shell with `python manage.py createsuperuser`.

The manifest requests a persistent disk for private uploaded documents and uses Render's pre-deploy migration command, which is available on paid web-service plans. Render web instances, PostgreSQL, and persistent disks may incur charges; review current pricing before creating resources. Uploaded document contents are not exposed through a public media URL. Back up the database and disk independently.

### Deploy the frontend to GitHub Pages

1. In GitHub, open **Settings → Pages** and set the build/deployment source to **GitHub Actions**.
2. Under **Settings → Secrets and variables → Actions → Variables**, add the repository variable `VITE_API_URL` with the deployed API base URL, such as `https://<your-backend-host>/api`. It must be HTTPS, must end in `/api`, and must not contain credentials. Do not put an OpenAI key or other secret in a `VITE_*` variable.
3. Push to `main` or run **Actions → Deploy Syntrix AI frontend to GitHub Pages → Run workflow**. The workflow tests the API client, builds the project with the `/syntrix-AI/` base path, and deploys `frontend/dist`. It intentionally fails the build if the backend URL is missing or invalid.

The frontend URL for this repository is `https://hari-unnikrishnan.github.io/syntrix-AI/`. Keep the deployed backend origin in `CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS`; local development can continue to use the local API fallback or `frontend/.env.local`.

### Other Python hosts

For Railway or another host, install `backend/requirements.txt`, run `python manage.py collectstatic --noinput`, apply `python manage.py migrate` as a release step, and start with `gunicorn syntrix_backend.wsgi:application --bind 0.0.0.0:$PORT` from `backend`. Set a generated `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, PostgreSQL `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `DJANGO_CSRF_TRUSTED_ORIGINS` through the host's private environment configuration. Set `DJANGO_SECURE_HSTS_SECONDS=31536000` only after HTTPS is confirmed; enable subdomain or preload policies only after verifying every affected hostname is HTTPS-only. Configure durable private storage for uploads and back up the database and files independently.

## Repository

[Syntrix AI on GitHub](https://github.com/hari-unnikrishnan/syntrix-AI)
