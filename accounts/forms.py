from django import forms
from django.contrib.auth.models import User


class RegisterForm(forms.Form):
    """Collects the fields needed to create a new account.

    Note: Django's built-in User model needs a `username`. To keep the
    registration form to the fields the spec asked for (no separate
    username field), the view uses the email address as the username.
    """

    full_name = forms.CharField(
        label="Full Name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Juana Dela Cruz",
            "autocomplete": "name",
        }),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "input",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "autocomplete": "new-password",
        }),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "autocomplete": "new-password",
        }),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data


class LoginForm(forms.Form):
    """Accepts an email (used as the username at registration) or a
    Django admin-created username, plus a password."""

    identifier = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "you@example.com",
            "autocomplete": "username",
        }),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "autocomplete": "current-password",
        }),
    )
