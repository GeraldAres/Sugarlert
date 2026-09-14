from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


def register_view(request):
    """Create user -> redirect to Login (per the required flow)."""
    if request.user.is_authenticated:
        return redirect("home:home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data["full_name"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=full_name,
            )
            messages.success(request, "Account created. Please log in.")
            return redirect("accounts:login")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Validate credentials -> Home on success, stay + show error on failure."""
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
                return redirect("home:home")
            form.add_error(None, "Invalid email/username or password.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Ends the session and returns the user to the Login Screen."""
    auth_logout(request)
    return redirect("accounts:login")
