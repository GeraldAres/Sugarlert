from django.shortcuts import redirect

from apps.home.models import UserProfile


class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not self._is_exempt(request.path_info):
            profile, _ = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={"display_name": request.user.get_full_name()},
            )
            request.user_profile = profile
            if not profile.onboarding_completed:
                return redirect("onboarding:start")
        return self.get_response(request)

    @staticmethod
    def _is_exempt(path):
        return path in {"/login", "/logout", "/register", "/onboarding"} or path.startswith(
            (
                "/login/",
                "/logout/",
                "/register/",
                "/onboarding/",
                "/static/",
                "/media/",
                "/admin/",
            )
        )
