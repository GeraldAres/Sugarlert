from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    DEFAULT_DAILY_SUGAR_LIMIT_G = 25

    class Sex(models.TextChoices):
        UNSET = "", "Select an option"
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class HealthStatus(models.TextChoices):
        UNSET = "", "Select an option"
        TYPE_1 = "type_1", "Type 1 diabetes"
        TYPE_2 = "type_2", "Type 2 diabetes"
        PREDIABETES = "prediabetes", "Prediabetes"
        GESTATIONAL = "gestational", "Gestational diabetes"
        NONE = "none", "No diagnosis / health-conscious"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class PrimaryGoal(models.TextChoices):
        UNSET = "", "Select an option"
        MANAGE_DIABETES = "manage_diabetes", "Manage diabetes"
        REDUCE_SUGAR = "reduce_sugar", "Reduce sugar intake"
        LOSE_WEIGHT = "lose_weight", "Lose weight"
        HEALTHY_EATING = "healthy_eating", "General healthy eating"

    class ActivityLevel(models.TextChoices):
        UNSET = "", "Select an option"
        SEDENTARY = "sedentary", "Sedentary"
        LIGHT = "light", "Light"
        MODERATE = "moderate", "Moderate"
        ACTIVE = "active", "Active"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    onboarding_completed = models.BooleanField(default=False)
    onboarding_step = models.PositiveSmallIntegerField(default=1)
    display_name = models.CharField(max_length=150, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=20, choices=Sex.choices, blank=True, default="")
    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(50), MaxValueValidator(250)],
    )
    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(20), MaxValueValidator(400)],
    )
    health_status = models.CharField(
        max_length=24,
        choices=HealthStatus.choices,
        blank=True,
        default="",
    )
    year_diagnosed = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1900)],
    )
    uses_insulin_or_medication = models.BooleanField(null=True, blank=True)
    tracks_blood_glucose = models.BooleanField(null=True, blank=True)
    primary_goal = models.CharField(
        max_length=24,
        choices=PrimaryGoal.choices,
        blank=True,
        default="",
    )
    activity_level = models.CharField(
        max_length=16,
        choices=ActivityLevel.choices,
        blank=True,
        default="",
    )
    daily_sugar_limit_g = models.PositiveIntegerField(
        default=DEFAULT_DAILY_SUGAR_LIMIT_G,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
    )
    doctor_name = models.CharField(max_length=150, blank=True)
    doctor_clinic = models.CharField(max_length=200, blank=True)
    doctor_contact = models.CharField(max_length=100, blank=True)
    consent_accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"
        ordering = ["user__username"]
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"

    def __str__(self):
        return f"{self.user.get_username()} profile"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = timezone.localdate()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def bmi(self):
        if not self.height_cm or not self.weight_kg or self.height_cm <= 0:
            return None
        height_m = self.height_cm / Decimal("100")
        return (self.weight_kg / (height_m * height_m)).quantize(Decimal("0.1"))

    @property
    def bmi_category(self):
        value = self.bmi
        if value is None:
            return None
        if value < Decimal("18.5"):
            return "Underweight"
        if value < Decimal("25"):
            return "Healthy range"
        if value < Decimal("30"):
            return "Overweight"
        return "Obesity range"


class NutritionSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nutrition_settings",
    )
    daily_sugar_limit_g = models.DecimalField(max_digits=6, decimal_places=2)
    daily_carb_limit_g = models.DecimalField(max_digits=6, decimal_places=2)
    daily_calorie_limit = models.IntegerField()
    alerts_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "nutrition_settings"
        ordering = ["user__username"]
        verbose_name = "nutrition settings"
        verbose_name_plural = "nutrition settings"

    def __str__(self):
        return f"{self.user.get_username()} nutrition settings"


class Food(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=150)
    barcode = models.CharField(max_length=64)
    serving_size_g = models.DecimalField(max_digits=6, decimal_places=2)
    calories = models.DecimalField(max_digits=7, decimal_places=2)
    sugar_g = models.DecimalField(max_digits=6, decimal_places=2)
    carbs_g = models.DecimalField(max_digits=6, decimal_places=2)
    protein_g = models.DecimalField(max_digits=6, decimal_places=2)
    fat_g = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "food"
        ordering = ["name"]
        verbose_name = "food"
        verbose_name_plural = "foods"

    def __str__(self):
        return f"{self.name} ({self.brand})"


class ScanRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scan_records",
    )
    food = models.ForeignKey(
        Food,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scan_records",
    )
    barcode = models.CharField(max_length=64)
    image_path = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scan_record"
        ordering = ["-scanned_at"]
        verbose_name = "scan record"
        verbose_name_plural = "scan records"

    def __str__(self):
        return f"Scan {self.barcode} by {self.user.get_username()}"


class FoodLog(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="food_logs",
    )
    food = models.ForeignKey(
        Food,
        on_delete=models.PROTECT,
        related_name="food_logs",
    )
    servings = models.DecimalField(max_digits=5, decimal_places=2)
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    consumed_at = models.DateTimeField()

    class Meta:
        db_table = "food_log"
        ordering = ["-consumed_at"]
        verbose_name = "food log"
        verbose_name_plural = "food logs"

    def __str__(self):
        return f"{self.user.get_username()} — {self.food.name} ({self.meal_type})"


class FoodEntry(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    class ServingUnit(models.TextChoices):
        GRAM = "g", "g"
        MILLILITER = "ml", "ml"
        PIECE = "piece", "piece"
        CUP = "cup", "cup"

    class Allergen(models.TextChoices):
        MILK = "milk", "Milk"
        EGGS = "eggs", "Eggs"
        PEANUTS = "peanuts", "Peanuts"
        TREE_NUTS = "tree_nuts", "Tree nuts"
        SOY = "soy", "Soy"
        WHEAT_GLUTEN = "wheat_gluten", "Wheat/Gluten"
        FISH = "fish", "Fish"
        SHELLFISH = "shellfish", "Shellfish"
        SESAME = "sesame", "Sesame"
        NONE = "none", "None"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="food_entries",
    )
    food_name = models.CharField(max_length=200, verbose_name="Food name")
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    serving_size = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    serving_unit = models.CharField(max_length=10, choices=ServingUnit.choices)
    sugar_g = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Sugar (g)",
    )
    carbs_g = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name="Carbohydrates (g)",
    )
    calories = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    allergens = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    eaten_at = models.DateTimeField(default=timezone.now, verbose_name="Date/time eaten")

    class Meta:
        ordering = ["-eaten_at", "-pk"]
        verbose_name = "food entry"
        verbose_name_plural = "food entries"

    @property
    def allergen_labels(self):
        labels = dict(self.Allergen.choices)
        return [labels.get(value, str(value)) for value in self.allergens]

    def __str__(self):
        return f"{self.food_name} ({self.get_meal_type_display()})"


class Notification(models.Model):
    class NotifType(models.TextChoices):
        SUGAR_LIMIT = "sugar_limit", "Sugar Limit"
        CARB_LIMIT = "carb_limit", "Carb Limit"
        CALORIE_LIMIT = "calorie_limit", "Calorie Limit"
        SCAN_RESULT = "scan_result", "Scan Result"
        GENERAL = "general", "General"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    notif_type = models.CharField(max_length=30, choices=NotifType.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        verbose_name = "notification"
        verbose_name_plural = "notifications"

    def __str__(self):
        return f"{self.title} → {self.user.get_username()}"


class Pharmacy(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=30)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "pharmacy"
        ordering = ["name"]
        verbose_name = "pharmacy"
        verbose_name_plural = "pharmacies"

    def __str__(self):
        return self.name


class EducationalArticle(models.Model):
    class Category(models.TextChoices):
        NUTRITION = "nutrition", "Nutrition"
        DIABETES = "diabetes", "Diabetes"
        LIFESTYLE = "lifestyle", "Lifestyle"
        MEDICATION = "medication", "Medication"

    title = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=Category.choices)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField()

    class Meta:
        db_table = "educational_article"
        ordering = ["-published_at"]
        verbose_name = "educational article"
        verbose_name_plural = "educational articles"

    def __str__(self):
        return self.title
