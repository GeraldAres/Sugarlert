from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from apps.home.models import UserProfile
from apps.login.forms import RegisterForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data["full_name"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=full_name,
            )
            UserProfile.objects.get_or_create(
                user=user,
                defaults={"display_name": full_name},
            )
            auth_login(request, user)
            messages.success(request, "Your account is ready. Let's personalize your experience.")
            return redirect("onboarding:start")
    else:
        form = RegisterForm()

    return render(request, "register/register.html", {"form": form})


def register_redirect(request):
    return redirect("register:register")
