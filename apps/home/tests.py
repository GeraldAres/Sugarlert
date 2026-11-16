from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import FoodEntry


class FoodEntryHomeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="food-owner")
        self.home_url = reverse("home:home")

    def entry_data(self, **overrides):
        data = {
            "food_name": "Plain oatmeal",
            "meal_type": FoodEntry.MealType.BREAKFAST,
            "serving_size": "1",
            "serving_unit": FoodEntry.ServingUnit.CUP,
            "sugar_g": "2.5",
            "carbs_g": "27",
            "calories": "150",
            "allergens": [],
            "notes": "",
            "eaten_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        }
        data.update(overrides)
        return data

    def test_home_requires_login(self):
        response = self.client.get(self.home_url)

        self.assertRedirects(response, f"{reverse('login:login')}?next={self.home_url}")

    def test_valid_entry_is_saved_for_logged_in_user(self):
        self.client.force_login(self.user)

        response = self.client.post(self.home_url, self.entry_data(), follow=True)

        self.assertEqual(response.redirect_chain, [(self.home_url, 302)])
        self.assertContains(response, "Food entry saved.")
        self.assertContains(response, "Plain oatmeal")
        self.assertContains(response, "2.5g")
        self.assertContains(response, "27.0g")
        entry = FoodEntry.objects.get()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.food_name, "Plain oatmeal")
        self.assertEqual(entry.sugar_g, 2.5)

    def test_negative_sugar_is_rejected_and_form_values_are_preserved(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.home_url,
            self.entry_data(food_name="My breakfast", sugar_g="-1"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["open_food_modal"])
        self.assertIn("sugar_g", response.context["add_food_form"].errors)
        self.assertContains(response, "My breakfast")
        self.assertEqual(FoodEntry.objects.count(), 0)

    def test_none_allergen_cannot_be_combined(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.home_url,
            self.entry_data(allergens=[FoodEntry.Allergen.NONE, FoodEntry.Allergen.MILK]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("allergens", response.context["add_food_form"].errors)
        self.assertEqual(FoodEntry.objects.count(), 0)

    def test_user_sees_only_their_own_food_entries(self):
        other_user = get_user_model().objects.create_user(username="another-user")
        own_entry = FoodEntry.objects.create(
            user=self.user,
            food_name="My snack",
            meal_type=FoodEntry.MealType.SNACK,
            serving_size=1,
            serving_unit=FoodEntry.ServingUnit.PIECE,
            sugar_g=3,
            carbs_g=12,
            eaten_at=timezone.now(),
        )
        FoodEntry.objects.create(
            user=other_user,
            food_name="Private other user's food",
            meal_type=FoodEntry.MealType.LUNCH,
            serving_size=1,
            serving_unit=FoodEntry.ServingUnit.CUP,
            sugar_g=8,
            carbs_g=30,
            eaten_at=timezone.now(),
        )
        self.client.force_login(self.user)

        response = self.client.get(self.home_url)

        self.assertContains(response, own_entry.food_name)
        self.assertNotContains(response, "Private other user's food")
        self.assertEqual(list(response.context["food_entries"]), [own_entry])
