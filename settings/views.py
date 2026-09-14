from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url="accounts:login")
def settings_view(request):
    return render(request, "settings/settings.html", {"user": request.user})
