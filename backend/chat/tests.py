from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import UserProfile, UserSettings

from .models import AIUsageLog, Conversation, Message, UploadedDocument
from .services import AIProviderUnavailable, generate_reply

User = get_user_model()


class AIServiceTests(SimpleTestCase):
    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="gpt-5.1")
    @patch("chat.services.OpenAI")
    def test_generate_reply_uses_responses_api(self, openai_client):
        history = [{"role": "user", "content": "Hello"}]
        client = openai_client.return_value
        client.responses.create.return_value = SimpleNamespace(
            output_text=" Hello from Syntrix. ",
            usage=SimpleNamespace(input_tokens=8, output_tokens=4),
        )

        result = generate_reply(history)

        openai_client.assert_called_once_with(
            api_key="test-key",
            timeout=45.0,
            max_retries=1,
        )
        client.responses.create.assert_called_once_with(
            model="gpt-5.1",
            instructions=(
                "You are Syntrix, a concise and helpful AI workspace "
                "assistant. Give clear, practical answers."
            ),
            input=history,
            max_output_tokens=1200,
        )
        self.assertEqual(result, ("Hello from Syntrix.", "live", {
            "input_tokens": 8,
            "output_tokens": 4,
        }))

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="gpt-5.1")
    @patch("chat.services.AuthenticationError", ValueError)
    @patch("chat.services.OpenAI")
    def test_invalid_api_key_has_safe_actionable_error(self, openai_client):
        openai_client.return_value.responses.create.side_effect = ValueError(
            "provider response contains secret details"
        )

        with self.assertRaises(AIProviderUnavailable) as raised:
            generate_reply([{"role": "user", "content": "Hello"}])

        self.assertIn("Check OPENAI_API_KEY", str(raised.exception))
        self.assertNotIn("secret details", str(raised.exception))

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="gpt-5.1")
    @patch("chat.services.RateLimitError", ValueError)
    @patch("chat.services.OpenAI")
    def test_rate_limit_has_actionable_error(self, openai_client):
        openai_client.return_value.responses.create.side_effect = ValueError(
            "provider rate limit details"
        )

        with self.assertRaises(AIProviderUnavailable) as raised:
            generate_reply([{"role": "user", "content": "Hello"}])

        self.assertIn("usage quota", str(raised.exception))
        self.assertNotIn("provider rate limit details", str(raised.exception))

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="gpt-5.1")
    @patch("chat.services.APIConnectionError", ConnectionError)
    @patch("chat.services.OpenAI")
    def test_network_failure_has_safe_retry_message(self, openai_client):
        openai_client.return_value.responses.create.side_effect = ConnectionError(
            "private network detail"
        )

        with self.assertRaises(AIProviderUnavailable) as raised:
            generate_reply([{"role": "user", "content": "Hello"}])

        self.assertIn("try again", str(raised.exception))
        self.assertNotIn("private network detail", str(raised.exception))


class ChatApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="workspace-user",
            email="user@example.com",
            password="secure-password-123",
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_chat_creates_persistent_demo_conversation(self):
        response = self.client.post(
            reverse("chat"),
            {"message": "Help me plan my day"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["mode"], "demo")
        conversation = Conversation.objects.get(user=self.user)
        self.assertEqual(conversation.messages.count(), 2)
        self.assertEqual(response.data["assistant_message"]["role"], "assistant")
        self.assertIn("DEMO MODE", response.data["assistant_message"]["content"])
        usage = AIUsageLog.objects.get(user=self.user)
        self.assertEqual(usage.provider, "demo")
        self.assertEqual(usage.status, AIUsageLog.Status.SUCCEEDED)

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="gpt-5.1")
    @patch("chat.services.OpenAI")
    def test_chat_returns_and_persists_live_openai_response(self, openai_client):
        openai_client.return_value.responses.create.return_value = SimpleNamespace(
            output_text="Here is a thoughtful email draft.",
            usage=SimpleNamespace(input_tokens=12, output_tokens=18),
        )

        response = self.client.post(
            reverse("chat"),
            {"message": "Draft a thoughtful email"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["mode"], "live")
        self.assertEqual(
            response.data["assistant_message"]["content"],
            "Here is a thoughtful email draft.",
        )
        self.assertEqual(
            Message.objects.filter(
                conversation__user=self.user,
                role=Message.Role.ASSISTANT,
            ).count(),
            1,
        )
        usage = AIUsageLog.objects.get(user=self.user)
        self.assertEqual(usage.status, AIUsageLog.Status.SUCCEEDED)
        self.assertEqual(usage.input_tokens, 12)
        self.assertEqual(usage.output_tokens, 18)
        self.assertEqual(usage.model, "gpt-5.1")

    def test_user_cannot_read_another_users_conversation(self):
        other_user = User.objects.create_user(
            username="other-user",
            password="secure-password-123",
        )
        conversation = Conversation.objects.create(
            user=other_user,
            title="Private conversation",
        )

        response = self.client.get(
            reverse("conversation-detail", args=[conversation.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_chat_requires_authentication(self):
        self.client.credentials()

        response = self.client.post(
            reverse("chat"),
            {"message": "Hello"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    @patch("chat.views.generate_reply", side_effect=AIProviderUnavailable("Unavailable"))
    def test_failed_ai_request_does_not_save_an_empty_conversation(self, _generate_reply):
        response = self.client.post(
            reverse("chat"),
            {"message": "Try this prompt"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(Conversation.objects.filter(user=self.user).exists())
        self.assertEqual(
            AIUsageLog.objects.get(user=self.user).status,
            AIUsageLog.Status.FAILED,
        )


class AuthenticationApiTests(APITestCase):
    def test_registration_creates_user_and_token(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-user",
                "email": "new@example.com",
                "password": "secure-password-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["token"])
        user = User.objects.get(username="new-user")
        self.assertTrue(user.check_password("secure-password-123"))
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertTrue(UserSettings.objects.filter(user=user).exists())

    def test_logout_revokes_token_and_requires_authentication(self):
        user = User.objects.create_user(
            username="logout-user",
            password="secure-password-123",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(reverse("logout"), format="json")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=user).exists())
        self.assertEqual(self.client.get(reverse("current-user")).status_code, 401)

        self.client.credentials()
        self.assertEqual(
            self.client.post(reverse("logout"), format="json").status_code,
            401,
        )

    def test_admin_login_sets_csrf_cookie_and_accepts_csrf_protected_post(self):
        admin_user = User.objects.create_superuser(
            username="csrf-admin",
            email="csrf-admin@example.com",
            password="secure-password-123",
        )
        client = Client(enforce_csrf_checks=True)

        login_page = client.get("/admin/login/")

        self.assertEqual(login_page.status_code, 200)
        self.assertIn("csrftoken", login_page.cookies)
        csrf_cookie = login_page.cookies["csrftoken"]
        self.assertFalse(csrf_cookie["secure"])
        self.assertEqual(csrf_cookie["samesite"], "Lax")
        self.assertEqual(csrf_cookie["path"], "/")
        csrf_token = csrf_cookie.value

        login_response = client.post(
            "/admin/login/",
            {
                "username": admin_user.username,
                "password": "secure-password-123",
                "csrfmiddlewaretoken": csrf_token,
            },
        )

        self.assertEqual(login_response.status_code, 302)
        self.assertIn("sessionid", login_response.cookies)
        self.assertEqual(client.get("/admin/").status_code, 200)

    def test_admin_login_rejects_post_without_csrf_cookie(self):
        User.objects.create_superuser(
            username="csrf-reject-admin",
            email="csrf-reject-admin@example.com",
            password="secure-password-123",
        )
        client = Client(enforce_csrf_checks=True)

        response = client.post(
            "/admin/login/",
            {
                "username": "csrf-reject-admin",
                "password": "secure-password-123",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_login_rejects_invalid_csrf_token(self):
        User.objects.create_superuser(
            username="csrf-invalid-admin",
            email="csrf-invalid-admin@example.com",
            password="secure-password-123",
        )
        client = Client(enforce_csrf_checks=True)
        client.get("/admin/login/")
        client.cookies["csrftoken"] = "invalid"

        response = client.post(
            "/admin/login/",
            {
                "username": "csrf-invalid-admin",
                "password": "secure-password-123",
                "csrfmiddlewaretoken": "invalid",
            },
        )

        self.assertEqual(response.status_code, 403)


class WorkspaceDataApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="workspace-data-user",
            password="secure-password-123",
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_health_checks_database_connection(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["database"], "connected")
        self.assertNotIn("tables", response.data)
        self.assertNotIn("record_counts", response.data)

    def test_backend_root_redirects_to_health_endpoint(self):
        response = self.client.get("/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [("/api/health/", 302)])
        self.assertEqual(response.data["database"], "connected")

    def test_user_can_update_their_settings_and_profile(self):
        profile_response = self.client.patch(
            reverse("user-profile"),
            {"display_name": "Syntrix member"},
            format="json",
        )
        settings_response = self.client.patch(
            reverse("user-settings"),
            {"theme": "dark", "email_notifications": False},
            format="json",
        )

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(settings_response.status_code, 200)
        self.assertEqual(settings_response.data["theme"], "dark")
        self.assertFalse(settings_response.data["email_notifications"])

    @override_settings(MAX_DOCUMENT_UPLOAD_BYTES=1024)
    def test_document_upload_is_private_and_deletion_removes_file(self):
        with TemporaryDirectory() as media_root:
            with self.settings(MEDIA_ROOT=media_root):
                upload = SimpleUploadedFile(
                    "notes.txt",
                    b"private notes",
                    content_type="text/plain",
                )
                response = self.client.post(
                    reverse("document-list"),
                    {"file": upload},
                    format="multipart",
                )

                self.assertEqual(response.status_code, 201)
                document = UploadedDocument.objects.get(user=self.user)
                self.assertEqual(document.original_name, "notes.txt")
                stored_path = Path(document.file.path)
                self.assertTrue(stored_path.exists())

                delete_response = self.client.delete(
                    reverse("document-detail", args=[document.pk])
                )

                self.assertEqual(delete_response.status_code, 204)
                self.assertFalse(stored_path.exists())

    def test_document_rejects_unsupported_extensions(self):
        upload = SimpleUploadedFile(
            "payload.exe",
            b"not a supported document",
            content_type="application/octet-stream",
        )

        response = self.client.post(
            reverse("document-list"),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UploadedDocument.objects.filter(user=self.user).exists())

    @override_settings(MAX_DOCUMENT_UPLOAD_BYTES=10)
    def test_document_rejects_files_over_configured_limit(self):
        upload = SimpleUploadedFile(
            "large.txt",
            b"x" * 11,
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("document-list"),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UploadedDocument.objects.filter(user=self.user).exists())

    def test_usage_summary_only_contains_authenticated_users_data(self):
        AIUsageLog.objects.create(
            user=self.user,
            model="demo",
            provider="demo",
            input_tokens=7,
            output_tokens=11,
        )

        response = self.client.get(reverse("ai-usage-summary"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            {"requests": 1, "input_tokens": 7, "output_tokens": 11},
        )


class DatabaseDashboardApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="database-admin",
            email="database-admin@example.com",
            password="secure-password-123",
        )
        self.admin_token = Token.objects.create(user=self.admin)
        self.user = User.objects.create_user(
            username="database-user",
            email="database-user@example.com",
            password="secure-password-123",
            first_name="Record",
            last_name="User",
        )
        self.user_token = Token.objects.create(user=self.user)
        self.user.profile.display_name = "Record Profile"
        self.user.profile.bio = "Record profile bio"
        self.user.profile.save()
        self.user.settings.response_tone = "record-tone"
        self.user.settings.save()
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Record conversation",
        )
        self.message = Message.objects.create(
            conversation=self.conversation,
            role=Message.Role.USER,
            content="Record message content",
        )
        AIUsageLog.objects.create(
            user=self.user,
            conversation=self.conversation,
            model="record-model",
            input_tokens=3,
            output_tokens=5,
        )
        UploadedDocument.objects.create(
            user=self.user,
            conversation=self.conversation,
            original_name="record-document.txt",
            file="documents/record-document.txt",
            content_type="text/plain",
            size_bytes=16,
        )

    def test_staff_database_overview_returns_live_metadata_and_counts(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.admin_token.key}"
        )

        response = self.client.get(reverse("admin-database"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["database"]["status"],
            "connected",
        )
        self.assertEqual(response.data["database"]["engine"], "sqlite")
        self.assertTrue(response.data["database"]["name"])
        self.assertIn("users", response.data["tables"])
        self.assertEqual(response.data["record_counts"]["accounts.User"], 2)
        self.assertEqual(response.data["summary"]["messages"], 1)
        self.assertEqual(response.data["summary"]["documents"], 1)

    def test_database_records_require_staff_authentication(self):
        response = self.client.get(reverse("admin-database"))
        self.assertEqual(response.status_code, 401)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.user_token.key}")

        response = self.client.get(reverse("admin-database"), {"resource": "users"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_get_paginated_real_records_for_each_resource(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.admin_token.key}"
        )
        expected = {
            "users": ("Record", "username"),
            "profiles": ("Record Profile", "display_name"),
            "settings": ("record-tone", "response_tone"),
            "conversations": ("Record conversation", "title"),
            "messages": ("Record message", "content"),
            "usage_logs": ("record-model", "model_name"),
            "documents": ("record-document", "file_name"),
        }

        for resource, (search, field) in expected.items():
            with self.subTest(resource=resource):
                response = self.client.get(
                    reverse("admin-database"),
                    {
                        "resource": resource,
                        "search": search,
                        "page_size": 1,
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(len(response.data["results"]), 1)
                self.assertIn(field, response.data["results"][0])
                self.assertNotIn("password", response.data["results"][0])
                self.assertNotIn("token", response.data["results"][0])

        conversation_response = self.client.get(
            reverse("admin-database"),
            {"resource": "conversations", "search": "Record conversation"},
        )
        self.assertEqual(
            conversation_response.data["results"][0]["message_count"],
            1,
        )
        message_response = self.client.get(
            reverse("admin-database"),
            {"resource": "messages", "search": "Record message"},
        )
        self.assertEqual(
            message_response.data["results"][0]["conversation_id"],
            self.conversation.pk,
        )
        self.assertEqual(
            message_response.data["results"][0]["user_name"],
            "Record User",
        )

    def test_admin_database_validates_pagination_and_sort_fields(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {self.admin_token.key}"
        )

        invalid_page_size = self.client.get(
            reverse("admin-database"),
            {"resource": "users", "page_size": 1000},
        )
        invalid_sort = self.client.get(
            reverse("admin-database"),
            {"resource": "users", "sort": "password"},
        )

        self.assertEqual(invalid_page_size.status_code, 400)
        self.assertEqual(invalid_sort.status_code, 400)

    def test_django_admin_home_links_to_database_overview(self):
        client = Client()
        client.force_login(self.admin)

        response = client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open database overview")
        self.assertContains(response, "/admin/database/")

    def test_django_admin_database_overview_renders_live_record_counts(self):
        client = Client()
        client.force_login(self.admin)

        response = client.get("/admin/database/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Database overview")
        self.assertContains(response, "users")
        self.assertContains(response, "Conversation")
        self.assertContains(response, "Message")
        self.assertContains(response, "View records")
