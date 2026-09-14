from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required(login_url="login:login")
def profile_view(request):
    return render(request, "profile/profile.html", {"user": request.user})
