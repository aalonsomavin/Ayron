from django.shortcuts import redirect
from django.urls import reverse


PUBLIC_PATHS = [
    "/accounts/login/",
    "/accounts/logout/",
    "/admin/",
    "/static/",
    "/health",
]


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)
        if self._is_public_path(request.path):
            return self.get_response(request)
        next_url = request.get_full_path()
        login_url = reverse("accounts:login")
        redirect_to = f"{login_url}?next={next_url}" if next_url != "/" else login_url
        return redirect(redirect_to)

    def _is_public_path(self, path):
        path = path.rstrip("/") or "/"
        for public in PUBLIC_PATHS:
            clean = public.rstrip("/") or "/"
            if public.endswith("/"):
                if path == clean or path.startswith(clean + "/"):
                    return True
            else:
                if path == clean or path == clean + "/":
                    return True
        return False
