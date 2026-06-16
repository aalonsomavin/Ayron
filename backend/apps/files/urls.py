from django.urls import path

from . import views

app_name = "files"
urlpatterns = [
    path("<uuid:file_id>/download/", views.file_download, name="download"),
    path("<uuid:file_id>/preview/", views.file_preview, name="preview"),
]
