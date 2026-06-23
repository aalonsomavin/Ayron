from django.urls import path

from . import views

app_name = "files"
urlpatterns = [
    path("<uuid:file_id>/download/", views.file_download, name="download"),
    path("<uuid:file_id>/download/pdf/", views.file_download_pdf, name="download_pdf"),
    path("<uuid:file_id>/preview/", views.file_preview, name="preview"),
    path("<uuid:file_id>/rename/", views.file_rename, name="rename"),
    path("<uuid:file_id>/save/", views.file_save, name="save"),
    path("<uuid:file_id>/unsave/", views.file_unsave, name="unsave"),
    path("<uuid:file_id>/pin/", views.file_pin, name="pin"),
]
