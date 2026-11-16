from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import FoodEntryForm
from .models import FoodEntry


@login_required(login_url="login:login")
def home_view(request):
    form = FoodEntryForm(request.POST if request.method == "POST" else None)
    open_food_modal = False

    if request.method == "POST":
        if form.is_valid():
            food_entry = form.save(commit=False)
            food_entry.user = request.user
            food_entry.save()
            messages.success(request, "Food entry saved.")
            return redirect("home:home")
        open_food_modal = True

    today_entries = FoodEntry.objects.filter(
        user=request.user,
        eaten_at__date=timezone.localdate(),
    )
    totals = today_entries.aggregate(
        sugar=Sum("sugar_g"),
        carbs=Sum("carbs_g"),
    )

    return render(
        request,
        "home/home.html",
        {
            "user": request.user,
            "add_food_form": form,
            "food_entries": today_entries,
            "today_sugar": totals["sugar"] or Decimal("0"),
            "today_carbs": totals["carbs"] or Decimal("0"),
            "today_food_count": today_entries.count(),
            "open_food_modal": open_food_modal,
        },
    )
