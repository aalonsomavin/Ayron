from django.urls import path

from . import views

app_name = "dashboards"
urlpatterns = [
    path("saved/", views.saved_dashboards_list, name="saved_list"),
    path("<uuid:file_id>/", views.saved_dashboard_detail, name="detail"),
    path("<uuid:file_id>/preview/", views.saved_dashboard_preview, name="preview"),
]
