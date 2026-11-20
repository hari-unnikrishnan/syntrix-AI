from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.authtoken.models import TokenProxy

from accounts.models import UserProfile, UserSettings

from .models import AIUsageLog, Conversation, Message, UploadedDocument


class AdminManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_superuser(
            username="admin-manager",
            email="admin-manager@example.com",
            password="secure-password-123",
        )
        cls.user = user_model.objects.create_user(
            username="record-owner",
            email="record-owner@example.com",
            password="secure-password-123",
        )
        cls.profile = UserProfile.objects.get(user=cls.user)
        cls.profile.display_name = "Record owner profile"
        cls.profile.save()
        cls.settings = UserSettings.objects.get(user=cls.user)
        cls.conversation = Conversation.objects.create(
            user=cls.user,
            title="Saved conversation",
        )
        cls.message = Message.objects.create(
            conversation=cls.conversation,
            role=Message.Role.USER,
            content="Saved message content",
        )
        cls.usage = AIUsageLog.objects.create(
            user=cls.user,
            conversation=cls.conversation,
            model="test-model",
            input_tokens=12,
            output_tokens=8,
        )
        cls.document = UploadedDocument.objects.create(
            user=cls.user,
            conversation=cls.conversation,
            original_name="report.pdf",
            file="documents/1/private-secret.pdf",
            content_type="application/pdf",
            size_bytes=128,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_application_models_are_registered_and_records_are_browsable(self):
        models_and_expected_rows = (
            ("accounts_user", self.user.username),
            ("accounts_userprofile", self.profile.display_name),
            ("accounts_usersettings", self.user.username),
            ("chat_conversation", self.conversation.title),
            ("chat_message", self.message.content),
            ("chat_aiusagelog", "test-model"),
            ("chat_uploadeddocument", self.document.original_name),
        )

        for model in (
            get_user_model(),
            UserProfile,
            UserSettings,
            Conversation,
            Message,
            AIUsageLog,
            UploadedDocument,
        ):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)
        self.assertNotIn(TokenProxy, admin.site._registry)
        index_response = self.client.get(reverse("admin:index"))
        self.assertNotContains(index_response, "Auth Token")

        for model_name, expected_row in models_and_expected_rows:
            with self.subTest(model=model_name):
                response = self.client.get(
                    reverse(f"admin:{model_name}_changelist")
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_row)

    def test_user_can_be_created_without_exposing_password_hash(self):
        add_url = reverse("admin:accounts_user_add")
        response = self.client.post(
            add_url,
            {
                "username": "admin-created",
                "email": "admin-created@example.com",
                "password1": "secure-password-123",
                "password2": "secure-password-123",
            },
        )

        self.assertEqual(response.status_code, 302)
        created_user = get_user_model().objects.get(username="admin-created")
        self.assertTrue(created_user.check_password("secure-password-123"))

        response = self.client.get(
            reverse("admin:accounts_user_change", args=(self.user.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.user.password)

    def test_document_change_form_does_not_expose_private_file_path(self):
        response = self.client.get(
            reverse(
                "admin:chat_uploadeddocument_change",
                args=(self.document.pk,),
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.document.original_name)
        self.assertNotContains(response, "documents/1/private-secret.pdf")

    def test_anonymous_users_are_redirected_to_admin_login(self):
        client = Client()

        response = client.get(reverse("admin:chat_conversation_changelist"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

        client.force_login(self.user)
        response = client.get(reverse("admin:chat_conversation_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
