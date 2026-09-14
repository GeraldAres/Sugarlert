from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import redirect, render

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
                return redirect("home:home")
            form.add_error(None, "Invalid email/username or password.")
    else:
        form = LoginForm()

    return render(request, "login/login.html", {"form": form})


def logout_view(request):
    auth_logout(request)
    return redirect("login:login")
