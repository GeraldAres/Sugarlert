from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import FoodEntry, UserProfile
from .services import get_calendar_day_status, get_chart_statistics, get_month_calendar


class StatisticsServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="stats-owner")
        self.today = timezone.localdate()

    def create_entry(self, user, day, sugar, calories="100"):
        eaten_at = timezone.make_aware(
            datetime.combine(day, time(hour=12)),
            timezone.get_current_timezone(),
        )
        return FoodEntry.objects.create(
            user=user,
            food_name="Test food",
            meal_type=FoodEntry.MealType.SNACK,
            serving_size=1,
            serving_unit=FoodEntry.ServingUnit.PIECE,
            sugar_g=sugar,
            calories=calories,
            eaten_at=eaten_at,
        )

    def set_sugar_limit(self, user, limit="12"):
        UserProfile.objects.filter(user=user).update(
            daily_sugar_limit_g=int(limit),
            onboarding_completed=True,
        )

    def test_chart_aggregation_summarizes_days_and_scopes_data_to_user(self):
        other_user = get_user_model().objects.create_user(username="other-stats-user")
        self.set_sugar_limit(self.user)
        self.create_entry(self.user, self.today, "10", "100")
        self.create_entry(self.user, self.today, "5", "200")
        self.create_entry(self.user, self.today - timedelta(days=1), "5", None)
        self.create_entry(self.user, self.today - timedelta(days=8), "80", "800")
        self.create_entry(other_user, self.today, "99", "990")

        result = get_chart_statistics(self.user, 7, today=self.today)
        summary = result["summary"]

        self.assertEqual(len(result["daily"]), 7)
        self.assertEqual(result["daily"][-1]["sugar"], Decimal("15"))
        self.assertEqual(result["daily"][-1]["calories"], Decimal("300"))
        self.assertEqual(summary["total_entries"], 3)
        self.assertEqual(summary["average_sugar"], Decimal("20") / Decimal("7"))
        self.assertEqual(summary["average_calories"], Decimal("300") / Decimal("7"))
        self.assertEqual(summary["days_over_limit"], 1)
        self.assertEqual(summary["highest_sugar_day"]["date"], self.today)

    def test_chart_range_rejects_unsupported_day_counts(self):
        with self.assertRaises(ValueError):
            get_chart_statistics(self.user, 14, today=self.today)

    def test_calendar_status_uses_labels_for_each_limit_state(self):
        limit = Decimal("10")
        self.assertEqual(
            get_calendar_day_status(Decimal("0"), limit, 0),
            ("no_entries", "No entries", "—"),
        )
        self.assertEqual(
            get_calendar_day_status(Decimal("7"), limit, 1),
            ("under", "Under limit", "✓"),
        )
        self.assertEqual(
            get_calendar_day_status(Decimal("8"), limit, 1),
            ("near", "Near limit", "!"),
        )
        self.assertEqual(
            get_calendar_day_status(Decimal("11"), limit, 1),
            ("over", "Over limit", "!"),
        )
        self.assertEqual(
            get_calendar_day_status(Decimal("3"), None, 1),
            ("no_limit", "No limit set", "•"),
        )

    def test_calendar_month_navigation_crosses_year_boundaries(self):
        january = get_month_calendar(self.user, 2025, 1)
        december = get_month_calendar(self.user, 2024, 12)

        self.assertEqual(january["previous_month"], "2024-12")
        self.assertEqual(january["next_month"], "2025-02")
        self.assertEqual(december["previous_month"], "2024-11")
        self.assertEqual(december["next_month"], "2025-01")


class StatisticsViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="stats-view-owner")
        self.other_user = get_user_model().objects.create_user(username="stats-view-other")
        UserProfile.objects.filter(user__in=(self.user, self.other_user)).update(
            onboarding_completed=True
        )
        self.today = timezone.localdate()

    def create_entry(self, user, day, food_name, sugar="3"):
        eaten_at = timezone.make_aware(
            datetime.combine(day, time(hour=9)),
            timezone.get_current_timezone(),
        )
        return FoodEntry.objects.create(
            user=user,
            food_name=food_name,
            meal_type=FoodEntry.MealType.BREAKFAST,
            serving_size=1,
            serving_unit=FoodEntry.ServingUnit.CUP,
            sugar_g=sugar,
            calories=120,
            eaten_at=eaten_at,
        )

    def test_statistics_and_chart_endpoint_require_login(self):
        for url in (reverse("stats:stats"), reverse("stats:data")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login:login"), response.url)

    def test_day_detail_requires_login(self):
        url = reverse("stats:day", kwargs={"day": self.today.isoformat()})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login:login"), response.url)

    def test_invalid_day_and_month_return_not_found(self):
        self.client.force_login(self.user)

        invalid_day = self.client.get("/stats/day/2025-02-30/")
        invalid_month = self.client.get(reverse("stats:stats"), {"month": "2025-13"})

        self.assertEqual(invalid_day.status_code, 404)
        self.assertEqual(invalid_month.status_code, 404)

    def test_invalid_chart_range_returns_bad_request(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("stats:data"), {"range": "14"})

        self.assertEqual(response.status_code, 400)

    def test_calendar_renders_only_owned_day_status_and_navigation(self):
        UserProfile.objects.filter(user=self.user).update(daily_sugar_limit_g=10)
        self.create_entry(self.user, self.today, "My logged breakfast", "3")
        self.create_entry(self.other_user, self.today, "Private other breakfast", "80")
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("stats:stats"),
            {"month": self.today.strftime("%Y-%m")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Under limit")
        self.assertContains(response, "Previous month")
        self.assertContains(response, "Next month")
        self.assertNotContains(response, "Private other breakfast")

    def test_chart_and_day_detail_only_include_current_users_entries(self):
        own_entry = self.create_entry(self.user, self.today, "My logged breakfast")
        self.create_entry(self.other_user, self.today, "Private other breakfast", "80")
        self.client.force_login(self.user)

        chart_response = self.client.get(reverse("stats:data"), {"range": "7"})
        day_url = reverse("stats:day", kwargs={"day": self.today.isoformat()})
        day_response = self.client.get(day_url)

        self.assertEqual(chart_response.status_code, 200)
        self.assertEqual(chart_response.json()["summary"]["total_entries"], 1)
        self.assertEqual(day_response.status_code, 200)
        self.assertContains(day_response, own_entry.food_name)
        self.assertNotContains(day_response, "Private other breakfast")

    def test_delete_is_post_only_and_limited_to_owned_entries_on_that_day(self):
        own_entry = self.create_entry(self.user, self.today, "My logged breakfast")
        other_entry = self.create_entry(self.other_user, self.today, "Private other breakfast")
        self.client.force_login(self.user)
        own_url = reverse(
            "stats:delete_entry",
            kwargs={"day": self.today.isoformat(), "entry_id": own_entry.pk},
        )
        other_url = reverse(
            "stats:delete_entry",
            kwargs={"day": self.today.isoformat(), "entry_id": other_entry.pk},
        )

        self.assertEqual(self.client.get(own_url).status_code, 405)
        self.assertEqual(self.client.post(other_url).status_code, 404)
        response = self.client.post(own_url)

        self.assertRedirects(
            response,
            reverse("stats:day", kwargs={"day": self.today.isoformat()}),
        )
        self.assertFalse(FoodEntry.objects.filter(pk=own_entry.pk).exists())
        self.assertTrue(FoodEntry.objects.filter(pk=other_entry.pk).exists())
