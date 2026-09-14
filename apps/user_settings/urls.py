from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

app_name = "user_settings"

urlpatterns = [
    path("", login_required(views.settings_view), name="settings"),
]
