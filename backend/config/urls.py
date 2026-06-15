from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("chat/", include("apps.chat.urls")),
    path("", include("apps.core.urls")),
]
