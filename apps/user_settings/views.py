from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url="login:login")
def settings_view(request):
    return render(request, "user_settings/settings.html", {"user": request.user})
