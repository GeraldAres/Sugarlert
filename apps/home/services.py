import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import FoodEntry, UserProfile


ZERO = Decimal("0")


def get_daily_sugar_limit(user):
    limit = UserProfile.objects.filter(user=user).values_list(
        "daily_sugar_limit_g", flat=True
    ).first()
    if limit is None or limit < 1:
        limit = UserProfile.DEFAULT_DAILY_SUGAR_LIMIT_G
    return Decimal(limit)


def get_daily_aggregates(user, start_date, end_date):
    return list(
        FoodEntry.objects.filter(
            user=user,
            eaten_at__date__range=(start_date, end_date),
        )
        .annotate(day=TruncDate("eaten_at", tzinfo=timezone.get_current_timezone()))
        .values("day")
        .annotate(
            sugar=Sum("sugar_g"),
            calories=Sum("calories"),
            entry_count=Count("pk"),
        )
        .order_by("day")
    )


def get_chart_statistics(user, days, today=None):
    if days not in (7, 30):
        raise ValueError("The statistics range must be 7 or 30 days.")

    today = today or timezone.localdate()
    start_date = today - timedelta(days=days - 1)
    limit = get_daily_sugar_limit(user)
    aggregated = get_daily_aggregates(user, start_date, today)
    by_day = {row["day"]: row for row in aggregated}

    daily = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        row = by_day.get(day, {})
        daily.append(
            {
                "date": day,
                "sugar": row.get("sugar") or ZERO,
                "calories": row.get("calories") or ZERO,
                "entry_count": row.get("entry_count", 0),
            }
        )

    total_sugar = sum((item["sugar"] for item in daily), ZERO)
    total_calories = sum((item["calories"] for item in daily), ZERO)
    highest_sugar_day = max(
        (item for item in daily if item["entry_count"]),
        key=lambda item: item["sugar"],
        default=None,
    )
    days_over_limit = (
        sum(
            1
            for item in daily
            if item["entry_count"] and item["sugar"] > limit
        )
        if limit is not None
        else None
    )

    return {
        "daily": daily,
        "sugar_limit": limit,
        "summary": {
            "average_sugar": total_sugar / Decimal(days),
            "average_calories": total_calories / Decimal(days),
            "highest_sugar_day": highest_sugar_day,
            "total_entries": sum(item["entry_count"] for item in daily),
            "days_over_limit": days_over_limit,
        },
    }


def get_calendar_day_status(sugar_total, limit, entry_count):
    if not entry_count:
        return "no_entries", "No entries", "—"
    if limit is None:
        return "no_limit", "No limit set", "•"
    if sugar_total > limit:
        return "over", "Over limit", "!"
    if sugar_total >= limit * Decimal("0.8"):
        return "near", "Near limit", "!"
    return "under", "Under limit", "✓"


def get_month_calendar(user, year, month):
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    limit = get_daily_sugar_limit(user)
    aggregated = get_daily_aggregates(user, month_start, month_end)
    by_day = {row["day"]: row for row in aggregated}
    weeks = []

    for week in calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(year, month):
        cells = []
        for day_number in week:
            if not day_number:
                cells.append(None)
                continue
            day = date(year, month, day_number)
            row = by_day.get(day, {})
            sugar = row.get("sugar") or ZERO
            entry_count = row.get("entry_count", 0)
            status, status_label, status_icon = get_calendar_day_status(
                sugar, limit, entry_count
            )
            cells.append(
                {
                    "date": day,
                    "number": day_number,
                    "sugar": sugar,
                    "entry_count": entry_count,
                    "status": status,
                    "status_label": status_label,
                    "status_icon": status_icon,
                }
            )
        weeks.append(cells)

    previous_month = None
    next_month = None
    if year > 1 or month > 1:
        previous = month_start - timedelta(days=1)
        previous_month = previous.strftime("%Y-%m")
    if year < 9999 or month < 12:
        next_start = month_end + timedelta(days=1)
        next_month = next_start.strftime("%Y-%m")

    return {
        "year": year,
        "month": month,
        "month_label": month_start.strftime("%B %Y"),
        "weekdays": list(calendar.day_abbr),
        "weeks": weeks,
        "previous_month": previous_month,
        "next_month": next_month,
        "sugar_limit": limit,
    }


def get_day_totals(user, day):
    row = get_daily_aggregates(user, day, day)
    if not row:
        return {"sugar": ZERO, "calories": ZERO, "entry_count": 0}
    return {
        "sugar": row[0]["sugar"] or ZERO,
        "calories": row[0]["calories"] or ZERO,
        "entry_count": row[0]["entry_count"],
    }
