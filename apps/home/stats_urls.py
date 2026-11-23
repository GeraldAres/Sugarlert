from django.urls import path

from . import views

app_name = "stats"

urlpatterns = [
    path("", views.stats_view, name="stats"),
    path("data/", views.stats_data, name="data"),
    path("day/<str:day>/", views.stats_day, name="day"),
    path(
        "day/<str:day>/entry/<int:entry_id>/delete/",
        views.delete_food_entry,
        name="delete_entry",
    ),
]
