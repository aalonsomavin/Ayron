from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("chat/", include("apps.chat.urls")),
    path("files/", include("apps.files.urls")),
    path("dashboards/", include("apps.files.urls_pages")),
    path("sources/", include("apps.sources.urls")),
    path("automations/", include("apps.automations.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
