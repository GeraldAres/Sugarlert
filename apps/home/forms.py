from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import FoodEntry


class FoodEntryForm(forms.ModelForm):
    allergens = forms.MultipleChoiceField(
        choices=FoodEntry.Allergen.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    eaten_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )

    class Meta:
        model = FoodEntry
        fields = (
            "food_name",
            "meal_type",
            "serving_size",
            "serving_unit",
            "sugar_g",
            "carbs_g",
            "calories",
            "allergens",
            "notes",
            "eaten_at",
        )
        widgets = {
            "food_name": forms.TextInput(attrs={"maxlength": 200}),
            "serving_size": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "sugar_g": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "carbs_g": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "calories": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.setdefault("class", "food-input")
        self.fields["allergens"].widget.attrs["class"] = "food-allergen-options"
        if not self.is_bound and not self.initial.get("eaten_at"):
            self.initial["eaten_at"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    def clean_allergens(self):
        allergens = self.cleaned_data["allergens"]
        if FoodEntry.Allergen.NONE in allergens and len(allergens) > 1:
            raise ValidationError("Select None by itself, or choose one or more allergens.")
        return allergens

    def clean_eaten_at(self):
        return self.cleaned_data.get("eaten_at") or timezone.now()
