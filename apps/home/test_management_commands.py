from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from .management.commands.seed_demo import DEMO_USERNAME
from .models import FoodEntry, UserProfile


class SQLiteManagementCommandTests(TestCase):
    def test_check_db_skips_network_and_checks_sqlite_writability(self):
        output = StringIO()
        with patch(
            "apps.home.management.commands.check_db.socket.getaddrinfo",
            side_effect=AssertionError("SQLite mode must not resolve a hostname."),
        ):
            call_command("check_db", stdout=output)

        self.assertIn("SQLite mode active, skipping network checks.", output.getvalue())
        self.assertIn("SQLite database location is writable:", output.getvalue())

    @override_settings(DEBUG=True)
    def test_seed_demo_is_idempotent_and_creates_limit_statuses(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())

        user = get_user_model().objects.get(username=DEMO_USERNAME)
        profile = UserProfile.objects.get(user=user)
        entries = FoodEntry.objects.filter(user=user)

        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(profile.daily_sugar_limit_g, 25)
        self.assertEqual(entries.count(), 30)
        self.assertSetEqual(
            set(entries.values_list("sugar_g", flat=True)),
            {12, 22, 32},
        )

    @override_settings(DEBUG=False)
    def test_seed_demo_refuses_to_run_when_debug_is_disabled(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
