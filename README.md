# SugarLert (Login / Register / Home)

Scope: this is the initial Django skeleton for SugarLert, covering only the
Login, Register, and Home screens and the navigation flow between them.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/ — it redirects to the Login screen.

## Flow

1. `/login/` — enter the email you registered with (used as your username)
   and your password.
2. `/register/` — full name, email, password, confirm password. On submit,
   a user account is created and you're sent back to `/login/`.
3. `/home/` — shown after a successful login. Requires being logged in
   (`@login_required`); visiting it directly while logged out redirects to
   `/login/`.
4. `/logout/` — ends the session and returns to `/login/`.

## Notes

- No custom User model — `django.contrib.auth.models.User` is used as-is.
  The registration form's email is stored as both `email` and `username`.
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
