from django import forms
from django.utils import timezone

from apps.home.models import UserProfile


CONSENT_TEXT = (
    "I understand SugarLert is a tracking tool and not a substitute for professional "
    "medical advice, and I agree to store my health information to personalize my experience."
)


def _coerce_optional_boolean(value):
    return {"yes": True, "no": False}.get(value)


class StyledProfileModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs["class"] = "choice-cards"
            else:
                field.widget.attrs.setdefault("class", "profile-input")


class AboutYouForm(StyledProfileModelForm):
    class Meta:
        model = UserProfile
        fields = ("display_name", "date_of_birth", "sex")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "sex": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].required = True
        self.fields["date_of_birth"].widget.attrs["max"] = timezone.localdate().isoformat()

    def clean_display_name(self):
        value = self.cleaned_data["display_name"].strip()
        if not value:
            raise forms.ValidationError("Enter the name you’d like us to use.")
        return value

    def clean_date_of_birth(self):
        value = self.cleaned_data["date_of_birth"]
        if value > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return value


class BodyMetricsForm(StyledProfileModelForm):
    class Meta:
        model = UserProfile
        fields = ("height_cm", "weight_kg", "activity_level")
        widgets = {
            "height_cm": forms.NumberInput(attrs={"min": "50", "max": "250", "step": "0.1"}),
            "weight_kg": forms.NumberInput(attrs={"min": "20", "max": "400", "step": "0.1"}),
            "activity_level": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["height_cm"].required = True
        self.fields["weight_kg"].required = True
        self.fields["activity_level"].required = True


class HealthBackgroundForm(StyledProfileModelForm):
    year_diagnosed = forms.IntegerField(
        required=False,
        min_value=1900,
        widget=forms.NumberInput(attrs={"min": "1900", "data-year-diagnosed": "true"}),
    )
    uses_insulin_or_medication = forms.TypedChoiceField(
        choices=(("", "Prefer not to say"), ("yes", "Yes"), ("no", "No")),
        coerce=_coerce_optional_boolean,
        required=False,
        empty_value=None,
        widget=forms.RadioSelect,
        label="Do you use insulin or medication?",
    )
    tracks_blood_glucose = forms.TypedChoiceField(
        choices=(("", "Prefer not to say"), ("yes", "Yes"), ("no", "No")),
        coerce=_coerce_optional_boolean,
        required=False,
        empty_value=None,
        widget=forms.RadioSelect,
        label="Do you track your blood glucose?",
    )

    class Meta:
        model = UserProfile
        fields = (
            "health_status",
            "year_diagnosed",
            "uses_insulin_or_medication",
            "tracks_blood_glucose",
        )
        widgets = {"health_status": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["health_status"].required = True
        self.fields["year_diagnosed"].max_value = timezone.localdate().year
        self.fields["year_diagnosed"].widget.attrs["max"] = str(timezone.localdate().year)
        if self.instance.pk:
            for name in ("uses_insulin_or_medication", "tracks_blood_glucose"):
                value = getattr(self.instance, name)
                self.initial[name] = "yes" if value is True else "no" if value is False else ""

    def clean(self):
        cleaned_data = super().clean()
        health_status = cleaned_data.get("health_status")
        year = cleaned_data.get("year_diagnosed")
        diabetes_statuses = {
            UserProfile.HealthStatus.TYPE_1,
            UserProfile.HealthStatus.TYPE_2,
            UserProfile.HealthStatus.PREDIABETES,
            UserProfile.HealthStatus.GESTATIONAL,
        }
        if health_status not in diabetes_statuses:
            cleaned_data["year_diagnosed"] = None
        elif year:
            if year > timezone.localdate().year:
                self.add_error("year_diagnosed", "The diagnosis year cannot be in the future.")
            elif self.instance.date_of_birth and year < self.instance.date_of_birth.year:
                self.add_error(
                    "year_diagnosed",
                    "The diagnosis year cannot be before your birth year.",
                )
        return cleaned_data


class GoalsForm(StyledProfileModelForm):
    class Meta:
        model = UserProfile
        fields = ("primary_goal", "daily_sugar_limit_g")
        widgets = {
            "primary_goal": forms.RadioSelect,
            "daily_sugar_limit_g": forms.NumberInput(attrs={"min": "1", "max": "500", "step": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["primary_goal"].required = True
        self.fields["daily_sugar_limit_g"].required = True


class DoctorForm(StyledProfileModelForm):
    class Meta:
        model = UserProfile
        fields = ("doctor_name", "doctor_clinic", "doctor_contact")
        widgets = {
            "doctor_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "doctor_clinic": forms.TextInput,
            "doctor_contact": forms.TextInput(attrs={"autocomplete": "tel"}),
        }


class ConsentForm(forms.Form):
    accepted = forms.BooleanField(label=CONSENT_TEXT, required=True)
