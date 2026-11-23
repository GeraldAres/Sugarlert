from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SugarLertAuthFlowTests(TestCase):
    def test_user_can_register_and_login(self):
        response = self.client.post(
            reverse("register:register"),
            {
                "full_name": "Jane Smith",
                "email": "jane@example.com",
                "password": "TestPassword123",
                "confirm_password": "TestPassword123",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("onboarding:start"))
        self.assertTrue(get_user_model().objects.filter(email="jane@example.com").exists())

        self.client.logout()
        login_response = self.client.post(
            reverse("login:login"),
            {"identifier": "jane@example.com", "password": "TestPassword123"},
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertRedirects(login_response, reverse("onboarding:start"))
        self.assertContains(login_response, "Step 1 of 7")

    def test_profile_and_settings_require_login(self):
        response_profile = self.client.get(reverse("profile:profile"))
        response_settings = self.client.get(reverse("user_settings:settings"))

        self.assertEqual(response_profile.status_code, 302)
        self.assertEqual(response_settings.status_code, 302)

    def test_home_requires_login(self):
        response = self.client.get(reverse("home:home"))
        self.assertEqual(response.status_code, 302)

    def test_logout_is_post_only(self):
        user = get_user_model().objects.create_user(username="logout-owner")
        self.client.force_login(user)

        get_response = self.client.get(reverse("login:logout"))
        post_response = self.client.post(reverse("login:logout"))

        self.assertEqual(get_response.status_code, 405)
        self.assertEqual(post_response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
