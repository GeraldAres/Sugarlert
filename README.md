# SugarLert (Food Logging & Statistics)

SugarLert helps users log food and review daily sugar and calorie intake.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

$env:USE_SQLITE = "1"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Then open http://127.0.0.1:8000/ — it redirects to the Login screen.

### Local SQLite demo

Set `USE_SQLITE=1` explicitly to use the ignored local `db.sqlite3` instead of
Supabase. Django prints a warning while this mode is active. The demo seeder
refuses to run unless `DEBUG=True` and the selected database is SQLite.

Demo-only login:

- Email/username: `demo@sugarlert.local`
- Password: `SugarLert-Demo-Only-2026!`

These credentials are only for the local demo account; do not reuse them for
real accounts or deployments. To switch back to Supabase in PowerShell, remove
the variable with `Remove-Item Env:USE_SQLITE`; confirm connectivity before
running database commands.

## Flow

1. `/login/` — enter the email you registered with (used as your username)
   and your password.
2. `/register/` — create an account with your name and email. You are signed
   in and guided through onboarding.
3. `/onboarding/` — complete the consent, health background, goals, and daily
   sugar limit steps. Progress is saved so you can resume later. Doctor details
   are optional.
4. `/home/` — log food and review today's totals. Users complete onboarding
   before reaching the dashboard.
5. `/profile/` — review or edit your health profile and optional doctor details.
6. `/stats/` — review 7- or 30-day sugar and calorie trends and browse the
   monthly food-log calendar. Select a date to view its entries and daily
   totals; entries can be deleted from the day detail page.
7. `/logout/` — ends the session and returns to `/login/`.

The Statistics screen loads chart data from `/stats/data/` and uses Chart.js
from a CDN. The calendar and day details use the existing `FoodEntry` records.

## Notes

- No custom User model — `django.contrib.auth.models.User` is used as-is.
  The registration form's email is stored as both `email` and `username`.
- Health background and onboarding data extend the existing `UserProfile`
  model in `apps.home`; the profile and onboarding screens live in `apps.profile`.
- `forms.py` was added (not in the original file list) to keep validation
  logic — password match check, duplicate-email check — out of `views.py`.
  `base.html` was also added so the three screens share one stylesheet
  instead of repeating `<head>`/CSS in each template.
- Password strength rules (`AUTH_PASSWORD_VALIDATORS` in `settings.py`) are
  configured but not yet wired into the registration form — add a call to
  `django.contrib.auth.password_validation.validate_password` in
  `RegisterForm.clean_password` if you want them enforced.
- `SECRET_KEY` is a placeholder. Replace it with an environment variable
  before deploying anywhere public.
