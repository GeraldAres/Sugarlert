from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.home.models import UserProfile

from .forms import AboutYouForm, BodyMetricsForm, ConsentForm
from .middleware import OnboardingMiddleware


class UserProfileModelTests(TestCase):
    def test_user_creation_automatically_creates_incomplete_profile(self):
        user = get_user_model().objects.create_user(
            username="profile-owner",
            first_name="Alex Morgan",
        )

        profile = UserProfile.objects.get(user=user)

        self.assertFalse(profile.onboarding_completed)
        self.assertEqual(profile.onboarding_step, 1)
        self.assertEqual(profile.display_name, "Alex Morgan")
        self.assertEqual(profile.daily_sugar_limit_g, 25)

    def test_age_bmi_and_category_are_computed_and_missing_values_are_safe(self):
        user = get_user_model().objects.create_user(username="metrics-owner")
        profile = user.profile
        self.assertIsNone(profile.age)
        self.assertIsNone(profile.bmi)
        self.assertIsNone(profile.bmi_category)

        today = timezone.localdate()
        profile.date_of_birth = date(today.year - 30, today.month, today.day)
        profile.height_cm = Decimal("175")
        profile.weight_kg = Decimal("70")
        profile.save()

        self.assertEqual(profile.age, 30)
        self.assertEqual(profile.bmi, Decimal("22.9"))
        self.assertEqual(profile.bmi_category, "Healthy range")


class OnboardingFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="onboarding-owner",
            first_name="New Member",
        )
        self.profile = self.user.profile
        self.client.force_login(self.user)
        self.onboarding_url = reverse("onboarding:start")

    def test_onboarding_middleware_exempts_auth_static_media_and_admin_paths(self):
        for path in (
            "/onboarding/",
            "/login/",
            "/logout/",
            "/register/",
            "/static/css/app.css",
            "/media/avatar.png",
            "/admin/",
        ):
            with self.subTest(path=path):
                self.assertTrue(OnboardingMiddleware._is_exempt(path))

    def test_incomplete_user_is_redirected_from_home_stats_and_profile(self):
        for url in (
            reverse("home:home"),
            reverse("stats:stats"),
            reverse("profile:profile"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, self.onboarding_url)

    def test_completed_user_can_visit_app_and_is_redirected_from_onboarding(self):
        self.profile.onboarding_completed = True
        self.profile.save(update_fields=("onboarding_completed",))

        home_response = self.client.get(reverse("home:home"))
        profile_response = self.client.get(reverse("profile:profile"))
        onboarding_response = self.client.get(self.onboarding_url)

        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(profile_response.status_code, 200)
        self.assertRedirects(onboarding_response, reverse("profile:profile"))

    def test_missing_consent_cannot_advance(self):
        response = self.client.post(
            self.onboarding_url,
            {"step": "1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("accepted", response.context["form"].errors)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.consent_accepted_at)
        self.assertEqual(self.profile.onboarding_step, 1)

    def test_future_date_of_birth_is_rejected(self):
        self.profile.onboarding_step = 2
        self.profile.save(update_fields=("onboarding_step",))
        future_date = timezone.localdate() + timedelta(days=1)

        response = self.client.post(
            f"{self.onboarding_url}?step=2",
            {
                "step": "2",
                "display_name": "Alex",
                "date_of_birth": future_date.isoformat(),
                "sex": UserProfile.Sex.PREFER_NOT_TO_SAY,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("date_of_birth", response.context["form"].errors)

    def test_impossible_height_and_weight_are_rejected(self):
        self.profile.onboarding_step = 3
        self.profile.save(update_fields=("onboarding_step",))

        response = self.client.post(
            f"{self.onboarding_url}?step=3",
            {
                "step": "3",
                "height_cm": "300",
                "weight_kg": "500",
                "activity_level": UserProfile.ActivityLevel.MODERATE,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("height_cm", response.context["form"].errors)
        self.assertIn("weight_kg", response.context["form"].errors)

    def test_form_classes_enforce_required_inputs(self):
        self.assertFalse(ConsentForm({}).is_valid())
        self.assertFalse(
            AboutYouForm(
                {
                    "display_name": "Alex",
                    "date_of_birth": "",
                    "sex": UserProfile.Sex.FEMALE,
                },
                instance=self.profile,
            ).is_valid()
        )
        self.assertFalse(
            BodyMetricsForm(
                {"height_cm": "10", "weight_kg": "5", "activity_level": "light"},
                instance=self.profile,
            ).is_valid()
        )

    def test_progress_resumes_after_logout(self):
        response = self.client.post(
            self.onboarding_url,
            {"step": "1", "accepted": "on"},
        )
        self.assertRedirects(response, f"{self.onboarding_url}?step=2")

        self.client.logout()
        self.client.force_login(self.user)
        resumed = self.client.get(self.onboarding_url)

        self.assertEqual(resumed.status_code, 200)
        self.assertContains(resumed, "Step 2 of 7")
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.consent_accepted_at)

    def test_doctor_step_can_be_skipped_and_onboarding_completed(self):
        self.profile.onboarding_step = 6
        self.profile.consent_accepted_at = timezone.now()
        self.profile.display_name = "New Member"
        self.profile.date_of_birth = date(1990, 4, 12)
        self.profile.sex = UserProfile.Sex.PREFER_NOT_TO_SAY
        self.profile.height_cm = Decimal("170")
        self.profile.weight_kg = Decimal("70")
        self.profile.activity_level = UserProfile.ActivityLevel.LIGHT
        self.profile.health_status = UserProfile.HealthStatus.NONE
        self.profile.primary_goal = UserProfile.PrimaryGoal.HEALTHY_EATING
        self.profile.save()

        skipped = self.client.post(
            f"{self.onboarding_url}?step=6",
            {"step": "6", "skip_doctor": "1"},
        )
        review = self.client.get(self.onboarding_url)
        finished = self.client.post(
            f"{self.onboarding_url}?step=7",
            {"step": "7", "finish": "1"},
        )

        self.assertEqual(skipped.status_code, 302)
        self.assertEqual(skipped.url, f"{self.onboarding_url}?step=7")
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, "Your doctor (optional)")
        self.assertRedirects(finished, reverse("home:home"))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.onboarding_completed)
        self.assertEqual(self.profile.doctor_name, "")

    def test_profile_page_never_displays_another_users_profile(self):
        self.profile.onboarding_completed = True
        self.profile.display_name = "Private Owner"
        self.profile.save()
        other_user = get_user_model().objects.create_user(username="other-profile")
        other_user.profile.display_name = "Other Private Name"
        other_user.profile.onboarding_completed = True
        other_user.profile.save()

        response = self.client.get(reverse("profile:profile"))

        self.assertContains(response, "Private Owner")
        self.assertNotContains(response, "Other Private Name")

    def test_profile_edit_updates_only_the_signed_in_users_doctor_details(self):
        self.profile.onboarding_completed = True
        self.profile.save(update_fields=("onboarding_completed",))
        other_user = get_user_model().objects.create_user(username="other-doctor")
        other_profile = other_user.profile
        other_profile.doctor_name = "Private Doctor"
        other_profile.save(update_fields=("doctor_name",))

        response = self.client.post(
            reverse("profile:edit", kwargs={"section": "doctor"}),
            {
                "doctor_name": "Dr. Example",
                "doctor_clinic": "Community Clinic",
                "doctor_contact": "555-0100",
            },
        )

        self.assertRedirects(response, reverse("profile:profile"))
        self.profile.refresh_from_db()
        other_profile.refresh_from_db()
        self.assertEqual(self.profile.doctor_name, "Dr. Example")
        self.assertEqual(other_profile.doctor_name, "Private Doctor")


class OnboardingEndToEndTests(TestCase):
    def test_registration_onboarding_and_private_features_work_with_csrf(self):
        client = Client(enforce_csrf_checks=True)
        login_url = reverse("login:login")
        register_url = reverse("register:register")
        onboarding_url = reverse("onboarding:start")

        self.assertEqual(client.get(login_url).status_code, 200)
        self.assertEqual(client.get(register_url).status_code, 200)
        register_response = client.post(
            register_url,
            {
                "full_name": "End-to-End Member",
                "email": "e2e-member@example.test",
                "password": "TestPassword123",
                "confirm_password": "TestPassword123",
            },
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertRedirects(register_response, onboarding_url, fetch_redirect_response=False)

        def post_onboarding(step, values):
            step_url = f"{onboarding_url}?step={step}"
            response = client.get(step_url)
            self.assertEqual(response.status_code, 200)
            return client.post(
                step_url,
                {"step": str(step), **values},
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            )

        self.assertContains(client.get(onboarding_url), "Step 1 of 7")
        self.assertEqual(
            post_onboarding(1, {"accepted": "on"}).status_code,
            302,
        )
        self.assertEqual(
            post_onboarding(
                2,
                {
                    "display_name": "End-to-End Member",
                    "date_of_birth": "1990-06-15",
                    "sex": UserProfile.Sex.PREFER_NOT_TO_SAY,
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            post_onboarding(
                3,
                {
                    "height_cm": "170",
                    "weight_kg": "70",
                    "activity_level": UserProfile.ActivityLevel.MODERATE,
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            post_onboarding(
                4,
                {
                    "health_status": UserProfile.HealthStatus.NONE,
                    "year_diagnosed": "",
                    "uses_insulin_or_medication": "",
                    "tracks_blood_glucose": "",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            post_onboarding(
                5,
                {
                    "primary_goal": UserProfile.PrimaryGoal.HEALTHY_EATING,
                    "daily_sugar_limit_g": "25",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            post_onboarding(6, {"skip_doctor": "1"}).status_code,
            302,
        )
        self.assertContains(client.get(onboarding_url), "Review your answers")
        finish_response = post_onboarding(7, {"finish": "1"})
        self.assertRedirects(
            finish_response,
            reverse("home:home"),
            fetch_redirect_response=False,
        )

        home_response = client.get(reverse("home:home"))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, reverse("login:logout"))
        self.assertEqual(client.get(reverse("user_settings:settings")).status_code, 200)
        food_response = client.post(
            reverse("home:home"),
            {
                "food_name": "Smoke-test oatmeal",
                "meal_type": "breakfast",
                "serving_size": "1",
                "serving_unit": "cup",
                "sugar_g": "4",
                "carbs_g": "20",
                "calories": "150",
                "allergens": [],
                "notes": "",
                "eaten_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            },
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertRedirects(
            food_response,
            reverse("home:home"),
            fetch_redirect_response=False,
        )

        stats_url = reverse("stats:stats")
        stats_response = client.get(stats_url)
        self.assertEqual(stats_response.status_code, 200)
        self.assertContains(stats_response, "chart.js@4.4.8")
        chart_response = client.get(reverse("stats:data"), {"range": "7"})
        self.assertEqual(chart_response.status_code, 200)
        self.assertEqual(chart_response.json()["summary"]["total_entries"], 1)

        today = timezone.localdate().isoformat()
        self.assertEqual(
            client.get(reverse("stats:day", kwargs={"day": today})).status_code,
            200,
        )
        self.assertEqual(client.get(reverse("profile:profile")).status_code, 200)

        doctor_edit_url = reverse("profile:edit", kwargs={"section": "doctor"})
        self.assertEqual(client.get(doctor_edit_url).status_code, 200)
        edit_response = client.post(
            doctor_edit_url,
            {
                "doctor_name": "Dr. Demo",
                "doctor_clinic": "Local Clinic",
                "doctor_contact": "555-0100",
            },
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertRedirects(
            edit_response,
            reverse("profile:profile"),
            fetch_redirect_response=False,
        )
