from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.home.models import UserProfile

from .forms import LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=identifier, password=password)
            if user is not None:
                auth_login(request, user)
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"display_name": user.get_full_name()},
                )
                if not profile.onboarding_completed:
                    return redirect("onboarding:start")
                return redirect("home:home")
            form.add_error(None, "Invalid email/username or password.")
    else:
        form = LoginForm()

    return render(request, "login/login.html", {"form": form})


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("login:login")
