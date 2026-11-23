from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

app_name = "profile"

urlpatterns = [
    path("", views.profile_view, name="profile"),
    path("edit/<slug:section>/", views.profile_edit_view, name="edit"),
]
