from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FoodEntryForm
from .models import FoodEntry
from .services import (
    get_chart_statistics,
    get_day_totals,
    get_month_calendar,
)


@login_required(login_url="login:login")
def home_view(request):
    form = FoodEntryForm(request.POST if request.method == "POST" else None)
    open_food_modal = request.GET.get("add_food") == "1"

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

@login_required(login_url="login:login")
def stats_view(request):
    month_value = request.GET.get("month")
    if month_value is None:
        selected_month = timezone.localdate().replace(day=1)
    else:
        try:
            if len(month_value) != 7 or month_value[4] != "-":
                raise ValueError
            selected_month = datetime.strptime(month_value, "%Y-%m").date()
            if selected_month.strftime("%Y-%m") != month_value:
                raise ValueError
        except ValueError:
            raise Http404("Invalid calendar month.")

    calendar_data = get_month_calendar(
        request.user, selected_month.year, selected_month.month
    )
    return render(
        request,
        "stats/stats.html",
        {
            "calendar": calendar_data,
            "calendar_days": calendar_data["weeks"],
            "has_sugar_limit": calendar_data["sugar_limit"] is not None,
            "today": timezone.localdate(),
            "has_entries": FoodEntry.objects.filter(user=request.user).exists(),
            "chart_data_url": reverse("stats:data"),
        },
    )


@login_required(login_url="login:login")
def stats_data(request):
    range_value = request.GET.get("range", "7")
    if range_value not in {"7", "30"}:
        return JsonResponse(
            {"error": "The range must be either 7 or 30 days."}, status=400
        )

    days = int(range_value)
    statistics = get_chart_statistics(request.user, days)
    summary = statistics["summary"]
    highest = summary["highest_sugar_day"]
    return JsonResponse(
        {
            "range": days,
            "dates": [item["date"].isoformat() for item in statistics["daily"]],
            "daily_sugar": [float(item["sugar"]) for item in statistics["daily"]],
            "daily_calories": [float(item["calories"]) for item in statistics["daily"]],
            "sugar_limit_g": (
                float(statistics["sugar_limit"])
                if statistics["sugar_limit"] is not None
                else None
            ),
            "summary": {
                "average_sugar_g": float(summary["average_sugar"]),
                "average_calories": float(summary["average_calories"]),
                "highest_sugar_day": (
                    {
                        "date": highest["date"].isoformat(),
                        "sugar_g": float(highest["sugar"]),
                    }
                    if highest
                    else None
                ),
                "total_entries": summary["total_entries"],
                "days_over_limit": summary["days_over_limit"],
            },
        }
    )


@login_required(login_url="login:login")
def stats_day(request, day):
    selected_day = _validated_day(day)

    entries = FoodEntry.objects.filter(
        user=request.user,
        eaten_at__date=selected_day,
    )
    return render(
        request,
        "stats/day.html",
        {
            "day": selected_day,
            "entries": entries,
            "totals": get_day_totals(request.user, selected_day),
        },
    )


@login_required(login_url="login:login")
@require_POST
def delete_food_entry(request, day, entry_id):
    selected_day = _validated_day(day)

    entry = get_object_or_404(
        FoodEntry,
        pk=entry_id,
        user=request.user,
        eaten_at__date=selected_day,
    )
    entry.delete()
    messages.success(request, "Food entry deleted.")
    return redirect("stats:day", day=selected_day.isoformat())


def _validated_day(value):
    try:
        selected_day = parse_date(value)
    except ValueError as exc:
        raise Http404("Invalid date.") from exc
    if selected_day is None or selected_day.isoformat() != value:
        raise Http404("Invalid date.")
    return selected_day
