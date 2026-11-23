from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.home.models import FoodEntry, UserProfile


DEMO_USERNAME = "demo@sugarlert.local"
DEMO_PASSWORD = "SugarLert-Demo-Only-2026!"
DEMO_NOTE = "SugarLert local demo data"


class Command(BaseCommand):
    help = "Create a demo-only user and 30 days of local food entries."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is available only when DEBUG=True.")
        if connection.vendor != "sqlite":
            raise CommandError("seed_demo is available only with SQLite.")

        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={"email": DEMO_USERNAME, "first_name": "Demo Member"},
        )
        user.email = DEMO_USERNAME
        user.first_name = "Demo Member"
        user.is_active = True
        user.set_password(DEMO_PASSWORD)
        user.save(update_fields=("email", "first_name", "is_active", "password"))

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = "Demo Member"
        profile.onboarding_completed = True
        profile.onboarding_step = 7
        profile.date_of_birth = datetime(1990, 6, 15).date()
        profile.sex = UserProfile.Sex.PREFER_NOT_TO_SAY
        profile.height_cm = Decimal("170")
        profile.weight_kg = Decimal("70")
        profile.health_status = UserProfile.HealthStatus.NONE
        profile.primary_goal = UserProfile.PrimaryGoal.HEALTHY_EATING
        profile.activity_level = UserProfile.ActivityLevel.MODERATE
        profile.daily_sugar_limit_g = 25
        profile.consent_accepted_at = profile.consent_accepted_at or timezone.now()
        profile.save()

        today = timezone.localdate()
        start_day = today - timedelta(days=29)
        FoodEntry.objects.filter(user=user, notes=DEMO_NOTE).exclude(
            eaten_at__date__range=(start_day, today)
        ).delete()

        sugar_totals = (Decimal("12"), Decimal("22"), Decimal("32"))
        meal_types = (
            FoodEntry.MealType.BREAKFAST,
            FoodEntry.MealType.LUNCH,
            FoodEntry.MealType.SNACK,
        )
        created_count = 0
        for offset in range(30):
            day = start_day + timedelta(days=offset)
            eaten_at = timezone.make_aware(
                datetime.combine(day, time(hour=12)),
                timezone.get_current_timezone(),
            )
            sugar = sugar_totals[offset % len(sugar_totals)]
            _, created = FoodEntry.objects.update_or_create(
                user=user,
                food_name=f"Demo meal {day.isoformat()}",
                eaten_at=eaten_at,
                defaults={
                    "meal_type": meal_types[offset % len(meal_types)],
                    "serving_size": Decimal("1"),
                    "serving_unit": FoodEntry.ServingUnit.CUP,
                    "sugar_g": sugar,
                    "carbs_g": sugar + Decimal("18"),
                    "calories": Decimal(350 + (offset % 5) * 70),
                    "allergens": [],
                    "notes": DEMO_NOTE,
                },
            )
            created_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready for {DEMO_USERNAME}: 30 days of entries "
                f"({created_count} created, {30 - created_count} refreshed)."
            )
        )
        self.stdout.write(
            "This account is for local development only; see README.md for its demo-only password."
        )
