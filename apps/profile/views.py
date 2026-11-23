from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.home.models import UserProfile

from .forms import (
    AboutYouForm,
    BodyMetricsForm,
    ConsentForm,
    DoctorForm,
    GoalsForm,
    HealthBackgroundForm,
)


ONBOARDING_FORMS = {
    2: AboutYouForm,
    3: BodyMetricsForm,
    4: HealthBackgroundForm,
    5: GoalsForm,
    6: DoctorForm,
}

STEP_TITLES = {
    1: "A little about SugarLert",
    2: "About you",
    3: "Body metrics",
    4: "Health background",
    5: "Goals & daily limit",
    6: "Your doctor",
    7: "Review your answers",
}

PROFILE_EDIT_FORMS = {
    "about": AboutYouForm,
    "body": BodyMetricsForm,
    "health": HealthBackgroundForm,
    "goals": GoalsForm,
    "doctor": DoctorForm,
}


@login_required(login_url="login:login")
def onboarding_view(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.get_full_name()},
    )
    if profile.onboarding_completed:
        return redirect("profile:profile")

    requested_step = request.POST.get("step") if request.method == "POST" else request.GET.get("step")
    try:
        step = int(requested_step) if requested_step else profile.onboarding_step
    except (TypeError, ValueError):
        step = profile.onboarding_step
    if step < 1 or step > 7 or step > profile.onboarding_step:
        step = profile.onboarding_step

    form = None
    if step == 1:
        form = ConsentForm(
            request.POST if request.method == "POST" else None,
            initial={"accepted": profile.consent_accepted_at is not None},
        )
        if request.method == "POST" and form.is_valid():
            if profile.consent_accepted_at is None:
                profile.consent_accepted_at = timezone.now()
            profile.onboarding_step = max(profile.onboarding_step, 2)
            profile.save(
                update_fields=("consent_accepted_at", "onboarding_step", "updated_at")
            )
            return _onboarding_redirect(2)
    elif step == 7:
        if request.method == "POST" and request.POST.get("finish"):
            incomplete_step = _first_incomplete_step(profile)
            if incomplete_step is not None:
                profile.onboarding_step = max(profile.onboarding_step, incomplete_step)
                profile.save(update_fields=("onboarding_step", "updated_at"))
                return _onboarding_redirect(incomplete_step)
            profile.onboarding_completed = True
            profile.onboarding_step = 7
            profile.save(update_fields=("onboarding_completed", "onboarding_step", "updated_at"))
            display_name = profile.display_name or request.user.get_username()
            messages.success(request, f"Welcome to SugarLert, {display_name}.")
            return redirect("home:home")
    else:
        form_class = ONBOARDING_FORMS[step]
        form = form_class(
            request.POST if request.method == "POST" else None,
            instance=profile,
        )
        if request.method == "POST":
            if step == 6 and request.POST.get("skip_doctor"):
                profile.onboarding_step = max(profile.onboarding_step, 7)
                profile.save(update_fields=("onboarding_step", "updated_at"))
                return _onboarding_redirect(7)
            if form.is_valid():
                form.save()
                next_step = min(step + 1, 7)
                profile.onboarding_step = max(profile.onboarding_step, next_step)
                profile.save(update_fields=("onboarding_step", "updated_at"))
                return _onboarding_redirect(next_step)

    context = {
        "step": step,
        "step_count": 7,
        "step_title": STEP_TITLES[step],
        "progress_percent": int(step / 7 * 100),
        "back_step": step - 1 if step > 1 else None,
        "form": form,
        "review_sections": _review_sections(profile) if step == 7 else [],
        "diabetes_statuses": (
            UserProfile.HealthStatus.TYPE_1,
            UserProfile.HealthStatus.TYPE_2,
            UserProfile.HealthStatus.PREDIABETES,
            UserProfile.HealthStatus.GESTATIONAL,
        ),
    }
    return render(request, "profile/onboarding.html", context)


@login_required(login_url="login:login")
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.get_full_name()},
    )
    display_name = profile.display_name or request.user.get_full_name() or request.user.get_username()
    initials = "".join(part[0].upper() for part in display_name.split()[:2])
    return render(
        request,
        "profile/profile.html",
        {
            "profile": profile,
            "display_name": display_name,
            "initials": initials or display_name[:1].upper(),
            "has_doctor_details": any(
                (profile.doctor_name, profile.doctor_clinic, profile.doctor_contact)
            ),
            "medication_display": _yes_no_display(profile.uses_insulin_or_medication),
            "glucose_tracking_display": _yes_no_display(profile.tracks_blood_glucose),
        },
    )


@login_required(login_url="login:login")
def profile_edit_view(request, section):
    form_class = PROFILE_EDIT_FORMS.get(section)
    if form_class is None:
        raise Http404("Unknown profile section.")

    profile = get_object_or_404(UserProfile, user=request.user)
    form = form_class(
        request.POST if request.method == "POST" else None,
        instance=profile,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("profile:profile")

    return render(
        request,
        "profile/edit.html",
        {
            "form": form,
            "section": section,
            "section_title": {
                "about": "About you",
                "body": "Body metrics",
                "health": "Health background",
                "goals": "Goals & daily limit",
                "doctor": "Your doctor",
            }[section],
        },
    )


def _onboarding_redirect(step):
    return redirect(f"{reverse('onboarding:start')}?step={step}")


def _first_incomplete_step(profile):
    if profile.consent_accepted_at is None:
        return 1
    if not profile.display_name or not profile.date_of_birth or not profile.sex:
        return 2
    if profile.height_cm is None or profile.weight_kg is None or not profile.activity_level:
        return 3
    if not profile.health_status:
        return 4
    if not profile.primary_goal or profile.daily_sugar_limit_g < 1:
        return 5
    return None


def _review_sections(profile):
    yes_no = {True: "Yes", False: "No", None: "Prefer not to say"}
    return [
        {
            "title": "About you",
            "step": 2,
            "edit_url": "?step=2",
            "items": (
                ("Display name", profile.display_name),
                ("Date of birth", profile.date_of_birth),
                ("Sex", profile.get_sex_display()),
            ),
        },
        {
            "title": "Body metrics",
            "step": 3,
            "edit_url": "?step=3",
            "items": (
                ("Height", f"{profile.height_cm} cm"),
                ("Weight", f"{profile.weight_kg} kg"),
                ("Activity level", profile.get_activity_level_display()),
            ),
        },
        {
            "title": "Health background",
            "step": 4,
            "edit_url": "?step=4",
            "items": (
                ("Health status", profile.get_health_status_display()),
                (
                    "Year diagnosed",
                    profile.year_diagnosed or "Not provided",
                ),
                (
                    "Insulin or medication",
                    yes_no[profile.uses_insulin_or_medication],
                ),
                ("Tracks blood glucose", yes_no[profile.tracks_blood_glucose]),
            ),
        },
        {
            "title": "Goals & daily limit",
            "step": 5,
            "edit_url": "?step=5",
            "items": (
                ("Primary goal", profile.get_primary_goal_display()),
                ("Daily sugar limit", f"{profile.daily_sugar_limit_g} g"),
            ),
        },
        {
            "title": "Your doctor (optional)",
            "step": 6,
            "edit_url": "?step=6",
            "items": (
                ("Name", profile.doctor_name or "Not provided"),
                ("Clinic", profile.doctor_clinic or "Not provided"),
                ("Contact", profile.doctor_contact or "Not provided"),
            ),
        },
    ]


def _yes_no_display(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Prefer not to say"
